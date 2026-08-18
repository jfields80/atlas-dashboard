"""PTF-BRIGHTDATA-MARRIOTT-PILOT-001 -- a bounded five-property benchmark.

WHAT THIS MEASURES
------------------
Five Marriott properties whose pet policies are already known from manual work.
The pilot captures them with Bright Data as though nothing were known, and only
afterwards compares the capture with what we know. The comparison is the
measurement; the capture is the thing being measured.

THE BENCHMARK IS NOT AN INPUT
-----------------------------
:data:`BENCHMARK` is a separate structure from :data:`TARGET_SPECS`, and the
separation is structural rather than a convention:

* a :class:`~browser_capture.CaptureTarget` has no field a policy value could
  occupy -- a name, a URL, a property code and whatever the identity census
  already holds, and nothing else;
* ``browser_capture`` and ``marriott_surface`` do not import this module, so
  the capture path cannot reach the answers even by accident;
* nothing reads :data:`BENCHMARK` before :func:`compare_to_benchmark`, which
  runs after the artifacts are on disk.

A capture that disagrees with the benchmark is reported as a disagreement. It
is never corrected, and a field Bright Data did not find is never filled in
from what we already knew.

WHAT THIS PILOT DOES NOT DO
---------------------------
It changes no market authority, no partition, no exclusion registry, no routing
record and no approval. It publishes nothing. It stops before founder review.
``VERIFIED_NO_PETS_CANDIDATE`` is a CANDIDATE and the word is load-bearing:
Best Western's brand-wide ``petsAllowed:false`` boilerplate is already resting
under two Columbus exclusions, and a machine may not close that loop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.brightdata import client                  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG  # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MEMBRANE  # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS      # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO    # noqa: E402
from scripts.pettripfinder.site_data import normalize_name           # noqa: E402

WORK_ORDER = "PTF-BRIGHTDATA-MARRIOTT-PILOT-001"
PILOT_ID = "brightdata-marriott-pilot-001"
BRAND = "marriott"
PILOT_SIZE = 5
MARKET_ID = "detroit-ann-arbor-mi"

RAW_ROOT = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
            / PILOT_ID / "raw")
REPORT_DIR = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
              / "reports")
CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "identity_census" / ("%s.json" % MARKET_ID))

SUMMARY_REPORT = REPORT_DIR / ("%s_summary.json" % PILOT_ID.replace("-", "_"))
PROPERTY_REPORT = REPORT_DIR / ("%s_properties.json" % PILOT_ID.replace("-", "_"))
COMPARISON_REPORT = REPORT_DIR / ("%s_comparison.md" % PILOT_ID.replace("-", "_"))

#: What an earlier execution of this pilot taught us about the HARNESS rather
#: than about Bright Data. Kept in the committed report because a benchmark
#: that hides its own instrumentation defects is measuring the wrong thing.
HARNESS_NOTES: Tuple[str, ...] = (
    "Run 1 (2026-08-18, 5/5 captured, 6 attempts) lost one Bright Data "
    "session to a HARNESS failure, not a Bright Data block: "
    "'Page.screenshot: Timeout 30000ms exceeded ... waiting for fonts to "
    "load' on Courtyard Detroit Downtown. Playwright's 30 s default is not "
    "enough for a full-page capture of a Marriott overview page over a remote "
    "browser. Screenshots now carry their own %d ms budget."
    % BC.SCREENSHOT_TIMEOUT_MS,
    "Run 1 also recorded a policy-section screenshot for Courtyard Detroit "
    "Dearborn that was a uniform white rectangle: the page had not scrolled, "
    "the hotel-information section had mounted its DOM without painting, and "
    "the summary counted the FILE rather than the IMAGE. The capture now "
    "centres the block, waits for its bounding box to stop moving, checks the "
    "crop for a single flat colour, retakes once, and REFUSES to record a "
    "blank crop as an artifact.",
    "Both defects were in this repository's code. Neither was a refusal, a "
    "challenge, or a block by Marriott or by Bright Data.",
)

CLAUDE_FALLBACK_REQUIRED = "CLAUDE_FALLBACK_REQUIRED"
PUBLICATION_CANDIDATE = "PUBLICATION_CANDIDATE"
VERIFIED_NO_PETS_CANDIDATE = "VERIFIED_NO_PETS_CANDIDATE"
HOLD = "HOLD"


class PilotError(ValueError):
    """The pilot plan is invalid."""


# --------------------------------------------------------------------------- #
# The five properties. INPUTS ONLY.
# --------------------------------------------------------------------------- #

#: (slug, canonical name, URL). Frozen at exactly five, and the runner refuses
#: to widen: "a five-property pilot that quietly ran forty is not the thing
#: that was authorised".
TARGET_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("ac-hotel-ann-arbor-downtown",
     "AC Hotel Ann Arbor Downtown",
     "https://www.marriott.com/en-us/hotels/"
     "dtwad-ac-hotel-ann-arbor-downtown/overview/"),
    ("courtyard-detroit-downtown",
     "Courtyard by Marriott Detroit Downtown",
     "https://www.marriott.com/en-us/hotels/"
     "dtwdc-courtyard-detroit-downtown/overview/"),
    ("courtyard-detroit-dearborn",
     "Courtyard by Marriott Detroit Dearborn",
     "https://www.marriott.com/en-us/hotels/"
     "dttdb-courtyard-detroit-dearborn/overview/"),
    ("detroit-marriott-livonia",
     "Detroit Marriott Livonia",
     "https://www.marriott.com/en-us/hotels/"
     "dtwli-detroit-marriott-livonia/overview/"),
    ("detroit-metro-airport-marriott",
     "Detroit Metro Airport Marriott",
     "https://www.marriott.com/en-us/hotels/"
     "dtwrm-detroit-metro-airport-marriott/overview/"),
)


def _census_rows() -> Dict[str, Dict]:
    """Identity rows from the committed Detroit/Ann Arbor census, by URL.

    READ ONLY. The census is a market authority and this pilot does not write
    to it; it is consulted so that ``hotel_ref`` REFERENCES an existing
    identity instead of minting one, which is what
    ``policy_observation.hotel_ref`` exists to guarantee.
    """
    if not CENSUS_PATH.exists():
        return {}
    data = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    rows: Dict[str, Dict] = {}
    for row in data.get("hotels") or ():
        url = str(row.get("official_url") or "").strip()
        if url:
            rows[url] = row
    return rows


def build_targets() -> Tuple[BC.CaptureTarget, ...]:
    """The five capture targets, enriched from the census where it knows them.

    Two of the five (Courtyard Detroit Dearborn, Detroit Metro Airport
    Marriott) are NOT in the Detroit/Ann Arbor census -- the census holds a
    Dearborn Inn and a Delta Hotels Detroit Metro Airport, which are different
    properties with different codes, and joining to either would be a false
    join of exactly the kind M10 exists to prevent. Those two are marked
    ``census_matched=False`` and carry no census-derived identity signal, so
    their identity gate rests on the property code and the page's own name
    alone. That is weaker, it is recorded as weaker, and it is not hidden.
    """
    rows = _census_rows()
    targets: List[BC.CaptureTarget] = []
    for slug, hotel, url in TARGET_SPECS:
        row = rows.get(url)
        code = MS.property_code(url)
        if not code:
            raise PilotError("no property code in target URL %r" % url)
        if row:
            targets.append(BC.CaptureTarget(
                slug=slug, hotel=hotel, requested_url=url, property_code=code,
                market_id=MARKET_ID,
                normalized_name=str(row.get("normalized_name")
                                    or normalize_name(hotel)),
                identity_key=str(row.get("identity_key") or ""),
                street_identity=str(row.get("street_identity") or ""),
                expected_postal_code=str(row.get("postal_code") or ""),
                expected_street=str(row.get("address") or ""),
                census_matched=True,
                census_note="matched to the committed %s census on official_url"
                            % MARKET_ID))
        else:
            targets.append(BC.CaptureTarget(
                slug=slug, hotel=hotel, requested_url=url, property_code=code,
                market_id=MARKET_ID, normalized_name=normalize_name(hotel),
                census_matched=False,
                census_note="no row in the committed %s census carries this "
                            "official_url; the identity gate rests on the "
                            "property code and the page's own name, and no "
                            "census row was joined to it" % MARKET_ID))
    if len(targets) != PILOT_SIZE:
        raise PilotError("this pilot is bounded at %d properties; %d built"
                         % (PILOT_SIZE, len(targets)))
    return tuple(targets)


# --------------------------------------------------------------------------- #
# The benchmark. READ ONLY AFTER CAPTURE.
# --------------------------------------------------------------------------- #

#: What manual PTF work already established about these five properties.
#:
#: ``None`` means the benchmark says nothing about that field and the
#: comparison scores it BENCHMARK_SILENT rather than counting it against the
#: capture. ``fee_basis_withheld`` names the reason the basis must be ABSENT --
#: Dearborn's recurring charge is the deliberate contradiction case.
BENCHMARK: Dict[str, Dict] = {
    "ac-hotel-ann-arbor-downtown": {
        "expected_disposition": PUBLICATION_CANDIDATE,
        "pets_allowed": True,
        "pet_fee_minor": 15000,
        "fee_basis": enums.BASIS_PER_STAY,
        "fee_basis_withheld": None,
        "cleaning_fee_minor": None,
        "weight_limit_lb": 50.0,
        "pet_count_limit": 1,
        "species_allowed": None,
        "cats_allowed": None,
        "expected_phrases": ("Pets Welcome",
                             "Non-Refundable Pet Fee Per Stay: $150.00",
                             "Maximum Pet Weight: 50.0lbs",
                             "Maximum Number of Pets in Room: 1"),
    },
    "courtyard-detroit-downtown": {
        "expected_disposition": VERIFIED_NO_PETS_CANDIDATE,
        "pets_allowed": False,
        "pet_fee_minor": None,
        "fee_basis": None,
        "fee_basis_withheld": None,
        "cleaning_fee_minor": None,
        "weight_limit_lb": None,
        "pet_count_limit": None,
        "species_allowed": None,
        "cats_allowed": None,
        "expected_phrases": ("Pets Not Allowed",),
    },
    "courtyard-detroit-dearborn": {
        "expected_disposition": PUBLICATION_CANDIDATE,
        "pets_allowed": True,
        "pet_fee_minor": 2000,
        # The recurring $20 charge is stated per_day in the prose and per_night
        # in the labelled row on the SAME first-party surface. per_day is not
        # per_night under the frozen schema, so the basis must be WITHHELD as
        # SOURCE_CONTRADICTORY. A capture that reports either basis has
        # normalised a contradiction and FAILS this property.
        "fee_basis": None,
        "fee_basis_withheld": enums.SOURCE_CONTRADICTORY,
        "cleaning_fee_minor": 10000,
        "weight_limit_lb": 35.0,
        "pet_count_limit": 2,
        "species_allowed": None,
        "cats_allowed": None,
        "expected_phrases": ("Pets Welcome",
                             "Non-Refundable Pet Fee Per Stay: $100.00",
                             "Non-Refundable Pet Fee Per Night: $20.00",
                             "Maximum Pet Weight: 35.0lbs",
                             "Maximum Number of Pets in Room: 2"),
    },
    "detroit-marriott-livonia": {
        "expected_disposition": PUBLICATION_CANDIDATE,
        "pets_allowed": True,
        "pet_fee_minor": 15000,
        "fee_basis": enums.BASIS_PER_STAY,
        "fee_basis_withheld": None,
        "cleaning_fee_minor": None,
        "weight_limit_lb": 50.0,
        "pet_count_limit": 2,
        "species_allowed": ["dog"],
        "cats_allowed": False,
        "expected_phrases": ("Pets Welcome", "Dogs Only",
                             "Non-Refundable Pet Fee Per Stay: $150.00",
                             "Maximum Pet Weight: 50.0lbs",
                             "Maximum Number of Pets in Room: 2"),
    },
    "detroit-metro-airport-marriott": {
        "expected_disposition": PUBLICATION_CANDIDATE,
        "pets_allowed": True,
        "pet_fee_minor": 5000,
        "fee_basis": enums.BASIS_PER_STAY,
        "fee_basis_withheld": None,
        "cleaning_fee_minor": None,
        "weight_limit_lb": 45.0,
        "pet_count_limit": 2,
        "species_allowed": None,
        "cats_allowed": None,
        "expected_phrases": ("Pets Welcome",
                             "Non-Refundable Pet Fee Per Stay: $50.00",
                             "Maximum Pet Weight: 45.0lbs",
                             "Maximum Number of Pets in Room: 2"),
    },
}

#: The fields whose exactness the pass/fail gate is measured on.
CRITICAL_FIELDS: Tuple[str, ...] = (
    "pets_allowed", "pet_fee_minor", "fee_basis", "weight_limit_lb",
    "pet_count_limit", "cleaning_fee_minor", "species_allowed", "cats_allowed",
)

MATCH = "MATCH"
MISMATCH = "MISMATCH"
CAPTURE_ABSENT = "CAPTURE_ABSENT"
BENCHMARK_SILENT = "BENCHMARK_SILENT"


def _captured_value(field: str, extraction: Mapping, withheld: Mapping):
    """The capture's value for a benchmark field name, or ``None``."""
    if field == "pet_fee_minor":
        return extraction.get("pet_fee")
    if field == "cleaning_fee_minor":
        return extraction.get("cleaning_fee")
    if field == "weight_limit_lb":
        limit = extraction.get("weight_limit")
        if isinstance(limit, Mapping) and limit.get("unit") == enums.UNIT_LB:
            return limit.get("value")
        return None
    return extraction.get(field)


def compare_to_benchmark(slug: str, *, extraction: Mapping,
                         withheld: Mapping, block_text: str) -> Dict:
    """Capture vs. known PTF facts. Runs only after the artifacts exist.

    Nothing here writes back into the capture. A MISMATCH stays a MISMATCH.
    """
    expected = BENCHMARK[slug]
    fields: Dict[str, Dict] = {}
    for field in CRITICAL_FIELDS:
        want = expected.get(field)
        got = _captured_value(field, extraction, withheld)

        if field == "fee_basis" and expected.get("fee_basis_withheld"):
            # The benchmark demands ABSENCE plus a specific withholding reason.
            reason = withheld.get("fee_basis")
            verdict = (MATCH if got is None
                       and reason == expected["fee_basis_withheld"]
                       else MISMATCH)
            fields[field] = {
                "expected": "ABSENT (%s)" % expected["fee_basis_withheld"],
                "captured": got if got is not None else
                            ("ABSENT (%s)" % reason if reason else "ABSENT"),
                "verdict": verdict,
                "note": "the contradiction must survive; a basis here would "
                        "mean it was normalised away",
            }
            continue

        if want is None:
            fields[field] = {"expected": None, "captured": got,
                             "verdict": BENCHMARK_SILENT}
            continue
        if got is None:
            fields[field] = {"expected": want, "captured": None,
                             "verdict": CAPTURE_ABSENT}
            continue
        fields[field] = {"expected": want, "captured": got,
                         "verdict": MATCH if got == want else MISMATCH}

    scored = [f for f in fields.values()
              if f["verdict"] != BENCHMARK_SILENT]
    critical_exact = bool(scored) and all(f["verdict"] == MATCH for f in scored)

    collapsed = MS.collapse(block_text)
    phrases = {}
    for phrase in expected.get("expected_phrases") or ():
        phrases[phrase] = MS.collapse(phrase) in collapsed
    text_match = bool(phrases) and all(phrases.values())

    return {
        "slug": slug,
        "fields": fields,
        "critical_field_exactness": critical_exact,
        "expected_phrases": phrases,
        "policy_text_match": text_match,
        "scored_fields": len(scored),
        "mismatched_fields": sorted(k for k, v in fields.items()
                                    if v["verdict"] == MISMATCH),
        "absent_fields": sorted(k for k, v in fields.items()
                                if v["verdict"] == CAPTURE_ABSENT),
    }


# --------------------------------------------------------------------------- #
# Observation assembly and the existing contracts.
# --------------------------------------------------------------------------- #

def build_observation(target: BC.CaptureTarget, record: BC.AttemptRecord,
                      payload: Mapping, *, run_id: str) -> Dict:
    """A ``ptf-policy-observation/1.0`` record from a VALID capture.

    Emitted into the EXISTING contract without extension: every key here is in
    ``policy_observation.ALLOWED_FIELDS``, every extraction key is in
    ``EXTRACTION_FIELDS``, and every flag code is in ``FLAG_CODES``. If a
    Bright Data capture could not be expressed in this vocabulary, that would
    be a contract gap to report -- not a reason to add a key.
    """
    reading = payload["reading"]
    artifacts = payload["artifacts"]
    identity = record.identity or {}
    signals = identity.get("signals") or {}

    result = MS.to_extraction(
        reading,
        location="hotel-info pet-policy container (%s)" % payload["locator_id"])

    identity_check = {"name_on_page": signals.get("name_on_page") or record.title}
    for source_key, target_key in (("address_on_page", "address_on_page"),
                                   ("property_code_on_page", "property_code"),
                                   ("phone_on_page", "phone_on_page")):
        value = str(signals.get(source_key) or "").strip()
        if value:
            identity_check[target_key] = value

    html_artifact = (artifacts.get("files") or {}).get(PG.PRIMARY_ARTIFACT) or {}

    observation = {
        "obs_id": "%s::%s::attempt-%02d" % (run_id, target.slug, record.attempt),
        "contract_version": PO.CONTRACT_VERSION,
        "hotel_ref": target.hotel_ref(),
        "identity_check": identity_check,
        "source_url": record.final_url or target.requested_url,
        "source_type": "official_property_page",
        "authority_tier": PO.PT1_OFFICIAL_PROPERTY,
        "observed_at": (record.started_at or "")[:10],
        "retrieved_at": record.started_at,
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
    return observation


def _ladder_transcript(records: Sequence[BC.AttemptRecord]) -> List[Dict]:
    """The attempts translated into the existing ladder vocabulary."""
    return [{"step": "A", "attempt": r.attempt,
             "outcome": O.LADDER_OUTCOME_MAP[r.outcome],
             "source_attempted": r.requested_url,
             "capture_method": PG.CAPTURE_METHOD}
            for r in records]


def evaluate_with_existing_contracts(observation: Mapping,
                                     records: Sequence[BC.AttemptRecord]) -> Dict:
    """Membrane + readiness, unmodified, on this pilot's own output."""
    verdict = MEMBRANE.evaluate(observation)
    transcript = _ladder_transcript(records)
    blocked = any(entry["outcome"] in ("BLOCKED_403", "BLOCKED_CHALLENGE",
                                       "TIMEOUT") for entry in transcript)
    exhausted = all(entry["outcome"] in ("SUCCESS", "NO_POLICY_SECTION")
                    for entry in transcript)
    result = READINESS.derive([observation], blocked=blocked,
                              all_surfaces_reached=exhausted)
    return {"membrane": verdict.to_dict(), "readiness": result.to_dict(),
            "ladder_transcript": transcript}


def disposition_for(record: BC.AttemptRecord, observation: Optional[Mapping],
                    readiness_state: str) -> str:
    """The candidate state this capture may propose, and nothing stronger.

    Gated on :func:`outcomes.may_bear_evidence` first. A blank page, a
    challenge, an unhydrated shell or an identity mismatch can never reach a
    candidate state here, whatever else is true.
    """
    if not O.may_bear_evidence(record.outcome) or observation is None:
        return HOLD
    pets_allowed = (observation.get("extraction") or {}).get("pets_allowed")
    if pets_allowed is False and readiness_state in (
            READINESS.POLICY_NEGATIVE_CONFIRMED, READINESS.POLICY_CONFIRMED):
        return VERIFIED_NO_PETS_CANDIDATE
    if pets_allowed is True and readiness_state in READINESS.PUBLISHABLE_STATES:
        return PUBLICATION_CANDIDATE
    return HOLD


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

def _artifact_path(artifacts: Mapping, name: str) -> Optional[Path]:
    entry = (artifacts.get("files") or {}).get(name)
    return Path(entry["path"]) if entry and entry.get("path") else None


def _estimate_cost(encoded_bytes: int, rate_minor_per_gb: Optional[float]
                   ) -> Optional[float]:
    if rate_minor_per_gb is None or not encoded_bytes:
        return None
    return (encoded_bytes / 1e9) * rate_minor_per_gb


async def run_pilot(*, run_id: str, targets: Sequence[BC.CaptureTarget],
                    raw_root: Path) -> Dict:
    """Capture all five properties, sequentially, measuring as we go."""
    raw_root.mkdir(parents=True, exist_ok=True)

    pilot_before = client.read_usage("PILOT_USAGE_BEFORE")
    rate = client.implied_rate_usd_minor_per_gb(pilot_before)
    pilot_started = time.monotonic()

    properties: List[Dict] = []
    for target in targets:
        property_before = client.read_usage("PROPERTY_USAGE_BEFORE::%s"
                                            % target.slug)
        started = time.monotonic()
        records, payload = await BC.capture_property(target, run_dir=raw_root)
        elapsed = time.monotonic() - started
        property_after = client.read_usage("PROPERTY_USAGE_AFTER::%s"
                                           % target.slug)

        successful = next((r for r in records if r.outcome == O.VALID), None)
        entry: Dict = {
            "slug": target.slug,
            "hotel": target.hotel,
            "identity_key": target.identity_key or None,
            "census_matched": target.census_matched,
            "census_note": target.census_note,
            "brand": BRAND,
            "requested_url": target.requested_url,
            "property_code": target.property_code,
            "attempts": [r.to_dict() for r in records],
            "total_attempts": len(records),
            "successful_attempt": successful.attempt if successful else None,
            "outcomes": [r.outcome for r in records],
            "elapsed_seconds": round(elapsed, 3),
            "successful_attempt_seconds": (round(successful.elapsed_seconds, 3)
                                           if successful else None),
            "claude_fallback_required": successful is None,
            "usage": client.delta(property_before, property_after),
        }

        estimated_bytes = sum(int((r.network or {}).get("encoded_bytes") or 0)
                              for r in records)
        entry["estimated_traffic"] = {
            "encoded_bytes_all_attempts": estimated_bytes,
            "encoded_bytes_successful_attempt": (
                int((successful.network or {}).get("encoded_bytes") or 0)
                if successful else 0),
            "estimated_cost_usd_minor": _estimate_cost(estimated_bytes, rate),
            "rate_basis": ("zone month-to-date cost / bandwidth at "
                           "PILOT_USAGE_BEFORE" if rate else "unavailable"),
            "label": "ESTIMATED -- browser-reported transfer, not Bright Data "
                     "billing",
        }

        if successful is None:
            entry["disposition"] = CLAUDE_FALLBACK_REQUIRED
            entry["note"] = ("three fresh Bright Data sessions all failed; no "
                             "artifact was written and no evidence was "
                             "produced. Claude's attended browser was NOT used "
                             "-- this pilot measures Bright Data standalone.")
            properties.append(entry)
            continue

        observation = build_observation(target, successful, payload,
                                        run_id=run_id)
        contracts = evaluate_with_existing_contracts(observation, records)
        reading = payload["reading"]
        extraction_result = MS.to_extraction(
            reading, location="hotel-info pet-policy container (%s)"
                              % payload["locator_id"])

        artifacts = payload["artifacts"]
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

        comparison = compare_to_benchmark(
            target.slug, extraction=observation["extraction"],
            withheld=extraction_result.withheld,
            block_text=reading.block_text)

        entry.update({
            "policy_locator": payload["locator_id"],
            "policy_block_quote": reading.block_text,
            "policy_reading": reading.to_dict(),
            "observation": observation,
            "withheld_fields": dict(extraction_result.withheld),
            "non_inferences": list(extraction_result.non_inferences),
            "contracts": contracts,
            "publication_grade": grade.to_dict(),
            "benchmark_comparison": comparison,
            "artifacts": artifacts,
            "disposition": disposition_for(
                successful, observation,
                contracts["readiness"]["state"]),
        })
        properties.append(entry)

        _write_capture_manifest(run_id=run_id, target=target,
                                records=records, successful=successful,
                                payload=payload, entry=entry)

    pilot_after = client.read_usage("PILOT_USAGE_AFTER")
    return {
        "run_id": run_id,
        "work_order": WORK_ORDER,
        "pilot_id": PILOT_ID,
        "brand": BRAND,
        "properties": properties,
        "pilot_elapsed_seconds": round(time.monotonic() - pilot_started, 3),
        "usage": client.delta(pilot_before, pilot_after),
        "implied_rate_usd_minor_per_gb": rate,
        "optimization_enabled": BC.OPTIMIZATION_ENABLED,
        "optimization_note": BC.OPTIMIZATION_NOTE,
    }


def _write_capture_manifest(*, run_id: str, target: BC.CaptureTarget,
                            records: Sequence[BC.AttemptRecord],
                            successful: BC.AttemptRecord, payload: Mapping,
                            entry: Mapping) -> None:
    """The per-capture manifest, beside the artifacts it describes.

    Written only for a successful attempt, into the gitignored raw tree, and
    redacted before it touches the disk.
    """
    artifacts = payload["artifacts"]
    manifest = {
        "schema": "ptf-brightdata-capture-manifest/1.0",
        "work_order": WORK_ORDER,
        "run_id": run_id,
        "hotel": target.hotel,
        "identity_key": target.identity_key or None,
        "brand": BRAND,
        "requested_url": target.requested_url,
        "final_url": successful.final_url,
        "canonical_url": ((successful.identity or {}).get("signals") or {})
                         .get("canonical_url", ""),
        "property_code": target.property_code,
        "title": successful.title,
        "captured_at": successful.started_at,
        "successful_attempt": successful.attempt,
        "total_attempts": len(records),
        "attempt_outcomes": [{"attempt": r.attempt, "outcome": r.outcome,
                              "detail": r.detail} for r in records],
        "capture_engine": BC.CAPTURE_ENGINE,
        "automation": BC.AUTOMATION,
        "optimization_enabled": BC.OPTIMIZATION_ENABLED,
        "optimization_note": BC.OPTIMIZATION_NOTE,
        "identity_signals": (successful.identity or {}),
        "policy_surface_locator": payload["locator_id"],
        "policy_quote": payload["reading"].block_text,
        "interactions": list(successful.interactions),
        "artifacts": artifacts.get("files") or {},
        "policy_section_screenshot": artifacts.get("policy_section"),
        "policy_visible_in_viewport": artifacts.get("policy_visible_in_viewport"),
        "identity_visible_in_policy_screenshot":
            artifacts.get("identity_visible_in_policy_screenshot"),
        "identity_and_policy_in_one_frame":
            artifacts.get("identity_and_policy_in_one_frame"),
        "identity_linkage": artifacts.get("identity_linkage"),
        "observation": entry.get("observation"),
        "publication_grade": entry.get("publication_grade"),
        "authority_changed": False,
        "policy_authority_changed": False,
        "exclusions_changed": False,
        "seed_authority_changed": False,
        "founder_approvals_changed": False,
        "partition_changed": False,
        "routing_authority_changed": False,
    }
    path = Path(artifacts["attempt_dir"]) / "capture-manifest.json"
    path.write_text(json.dumps(client.redact(manifest), indent=2,
                               ensure_ascii=False, sort_keys=False),
                    encoding="utf-8")


# --------------------------------------------------------------------------- #
# Summary.
# --------------------------------------------------------------------------- #

def summarize(run: Mapping) -> Dict:
    """The pilot's metrics. Counting only; no judgement is added here."""
    properties = list(run.get("properties") or ())
    total = len(properties)

    def count(predicate) -> int:
        return sum(1 for p in properties if predicate(p))

    successes = [p for p in properties if p.get("successful_attempt")]
    total_attempts = sum(int(p.get("total_attempts") or 0) for p in properties)
    failed_attempts = sum(
        1 for p in properties for a in (p.get("attempts") or ())
        if a.get("outcome") != O.VALID)

    artifact_files = [((p.get("artifacts") or {}).get("files") or {})
                      for p in successes]
    estimated_bytes = sum(
        int((p.get("estimated_traffic") or {}).get(
            "encoded_bytes_all_attempts") or 0) for p in properties)
    rate = run.get("implied_rate_usd_minor_per_gb")
    estimated_cost = ((estimated_bytes / 1e9) * rate) if rate else None
    failed_bytes = estimated_bytes - sum(
        int((p.get("estimated_traffic") or {}).get(
            "encoded_bytes_successful_attempt") or 0) for p in properties)

    comparisons = [p.get("benchmark_comparison") or {} for p in successes]
    grades = [p.get("publication_grade") or {} for p in successes]

    contradiction = next(
        (p for p in successes if p["slug"] == "courtyard-detroit-dearborn"),
        None)
    contradiction_preserved = False
    if contradiction:
        fields = ((contradiction.get("benchmark_comparison") or {})
                  .get("fields") or {})
        contradiction_preserved = (fields.get("fee_basis", {}).get("verdict")
                                   == MATCH)

    elapsed = [float(p.get("elapsed_seconds") or 0) for p in properties]
    success_elapsed = [float(p.get("successful_attempt_seconds") or 0)
                       for p in successes]

    return {
        "schema": "ptf-brightdata-pilot-summary/1.0",
        "work_order": WORK_ORDER,
        "pilot_id": PILOT_ID,
        "run_id": run.get("run_id"),
        "total": total,
        "fetch_success": len(successes),
        "identity_match": count(
            lambda p: bool(((next((a for a in (p.get("attempts") or ())
                                   if a.get("outcome") == O.VALID), {}) or {})
                            .get("identity") or {}).get("confirmed"))),
        "policy_found": count(lambda p: bool(p.get("policy_locator"))),
        "policy_text_match": sum(1 for c in comparisons
                                 if c.get("policy_text_match")),
        "critical_field_match": sum(1 for c in comparisons
                                    if c.get("critical_field_exactness")),
        "verified_no_pets_match": count(
            lambda p: p.get("disposition") == VERIFIED_NO_PETS_CANDIDATE
            and BENCHMARK[p["slug"]]["expected_disposition"]
            == VERIFIED_NO_PETS_CANDIDATE),
        "false_verified_no_pets": count(
            lambda p: p.get("disposition") == VERIFIED_NO_PETS_CANDIDATE
            and BENCHMARK[p["slug"]]["expected_disposition"]
            != VERIFIED_NO_PETS_CANDIDATE),
        "contradiction_preserved": contradiction_preserved,
        "rendered_html": sum(1 for f in artifact_files
                             if PG.PRIMARY_ARTIFACT in f),
        "full_page_screenshot": sum(1 for f in artifact_files
                                    if "full-page.png" in f),
        # Counted from the RECORDED artifact, which a blank crop never
        # becomes. Run 1 counted file existence and reported 5/5 for a set
        # containing one uniform white rectangle.
        "policy_section_screenshot": sum(1 for f in artifact_files
                                         if "policy-section.png" in f),
        "identity_and_policy_in_one_frame": sum(
            1 for p in successes
            if (p.get("artifacts") or {}).get("identity_and_policy_in_one_frame")),
        "hash_validation": sum(1 for g in grades if g.get("hash_rederived")),
        "publication_grade_confirmed": sum(
            1 for g in grades if g.get("verdict") == PG.CONFIRMED),
        "publication_grade_rejected": total - sum(
            1 for g in grades if g.get("verdict") == PG.CONFIRMED),
        "claude_fallback_required": count(
            lambda p: p.get("claude_fallback_required")),
        "total_attempts": total_attempts,
        "failed_attempts": failed_attempts,
        "avg_attempts_per_property": (round(total_attempts / total, 3)
                                      if total else 0),
        "avg_seconds_per_property": (round(sum(elapsed) / total, 3)
                                     if total else 0),
        "avg_seconds_per_successful_property": (
            round(sum(success_elapsed) / len(successes), 3)
            if successes else None),
        "pilot_elapsed_seconds": run.get("pilot_elapsed_seconds"),
        "brightdata_reported": run.get("usage"),
        "estimated_traffic_bytes": estimated_bytes,
        "estimated_traffic_cost_usd_minor": (round(estimated_cost, 2)
                                             if estimated_cost else None),
        "estimated_failed_attempt_bytes": failed_bytes,
        "estimated_failed_attempt_cost_usd_minor": (
            round((failed_bytes / 1e9) * rate, 2) if rate else None),
        "implied_rate_usd_minor_per_gb": (round(rate, 2) if rate else None),
        "cost_status": (run.get("usage") or {}).get("cost_status"),
        "optimization_enabled": run.get("optimization_enabled"),
        "contract_integration_gaps": (grades[0].get("contract_integration_gaps")
                                      if grades else
                                      [g.to_dict() for g in PG.detect_gaps()]),
        "authority_changed": False,
        "policy_authority_changed": False,
        "exclusions_changed": False,
        "seed_authority_changed": False,
        "founder_approvals_changed": False,
        "partition_changed": False,
        "routing_authority_changed": False,
        "promotion_performed": False,
        "promotion_note": ("this pilot stops before founder review. Nothing "
                           "here writes to a market authority and no "
                           "disposition above is a decision."),
    }


def _write_json(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(client.redact(payload), indent=2,
                               ensure_ascii=False) + "\n", encoding="utf-8")


def render_comparison_markdown(run: Mapping, summary: Mapping) -> str:
    """The human-readable capture-vs-benchmark table."""
    lines = [
        "# %s -- Bright Data vs. known PetTripFinder facts" % WORK_ORDER,
        "",
        "Run `%s`. Capture engine: %s driven by %s."
        % (run.get("run_id"), BC.CAPTURE_ENGINE, BC.AUTOMATION),
        "",
        "The benchmark column is what manual PTF work already established. It "
        "was read only after every artifact was on disk, and no capture value "
        "below was corrected, filled in, or nudged towards it.",
        "",
        "| Property | Fetch | Identity | Policy | Text match | Critical fields "
        "| Publication grade | Disposition |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for prop in run.get("properties") or ():
        comparison = prop.get("benchmark_comparison") or {}
        grade = prop.get("publication_grade") or {}
        valid = bool(prop.get("successful_attempt"))
        identity = bool(((next((a for a in (prop.get("attempts") or ())
                                if a.get("outcome") == O.VALID), {}) or {})
                         .get("identity") or {}).get("confirmed"))
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            prop.get("hotel"),
            "%d/%d" % (prop.get("successful_attempt") or 0,
                       prop.get("total_attempts") or 0) if valid
            else "FAILED (%d attempts)" % (prop.get("total_attempts") or 0),
            "confirmed" if identity else "-",
            prop.get("policy_locator") or "-",
            "yes" if comparison.get("policy_text_match") else
            ("no" if comparison else "-"),
            "exact" if comparison.get("critical_field_exactness") else
            (", ".join(comparison.get("mismatched_fields") or
                       comparison.get("absent_fields") or ["-"])
             if comparison else "-"),
            grade.get("verdict") or "-",
            prop.get("disposition")))

    lines += ["", "## Field-by-field", ""]
    for prop in run.get("properties") or ():
        lines += ["### %s" % prop.get("hotel"), ""]
        comparison = prop.get("benchmark_comparison")
        if not comparison:
            # Every attempt is printed with what the browser actually landed
            # on. A property that ends CLAUDE_FALLBACK_REQUIRED is the most
            # informative row in the report and the least useful one to
            # summarise as "failed".
            lines += ["Capture failed after %d attempts; nothing to compare."
                      % (prop.get("total_attempts") or 0), "",
                      "| Attempt | Outcome | Title seen | Final URL | Body chars |",
                      "| --- | --- | --- | --- | --- |"]
            for attempt in prop.get("attempts") or ():
                lines.append("| %s | %s | %s | %s | %s |" % (
                    attempt.get("attempt"), attempt.get("outcome"),
                    (attempt.get("title") or "<blank>")[:70],
                    attempt.get("final_url") or "-",
                    attempt.get("body_chars")))
            lines += ["", "Claude's attended browser was NOT used: this pilot "
                          "measures Bright Data standalone, so the fallback is "
                          "reported rather than exercised.", ""]
            continue
        lines += ["| Field | Benchmark | Captured | Verdict |",
                  "| --- | --- | --- | --- |"]
        for field, result in comparison["fields"].items():
            lines.append("| %s | %s | %s | %s |"
                         % (field, result.get("expected"),
                            result.get("captured"), result.get("verdict")))
        withheld = prop.get("withheld_fields") or {}
        if withheld:
            lines += ["", "Withheld: %s."
                      % ", ".join("`%s` (%s)" % (k, v)
                                  for k, v in sorted(withheld.items()))]
        lines += ["", "Policy quote (verbatim, contiguous in the saved page "
                      "text):", "", "> %s" % prop.get("policy_block_quote"), ""]

    lines += ["", "## Harness notes", "",
              "Defects found in this repository's own instrumentation, "
              "recorded so the acquisition measurement is not credited or "
              "blamed for them:", ""]
    for note in HARNESS_NOTES:
        lines += ["- %s" % note]

    lines += ["", "## Contract integration gaps", ""]
    for gap in summary.get("contract_integration_gaps") or ():
        lines += ["**%s** -- %s" % (gap.get("code"), gap.get("summary")), "",
                  gap.get("detail") or "", "",
                  "_Contract: `%s`. Blocks publication: %s._"
                  % (gap.get("contract"), gap.get("blocks_publication")), ""]

    lines += ["", "## Authority", "",
              "POLICY_AUTHORITY_CHANGED: NO  ",
              "EXCLUSIONS_CHANGED: NO  ",
              "SEED_AUTHORITY_CHANGED: NO  ",
              "FOUNDER_APPROVALS_CHANGED: NO  ",
              "PARTITION_CHANGED: NO  ",
              "ROUTING_AUTHORITY_CHANGED: NO", ""]
    return "\n".join(lines)


def write_reports(run: Mapping, summary: Mapping) -> Dict[str, str]:
    """Committed, non-sensitive pilot outputs. Raw artifacts stay gitignored."""
    _write_json(SUMMARY_REPORT, summary)
    _write_json(PROPERTY_REPORT, {
        "schema": "ptf-brightdata-pilot-properties/1.0",
        "work_order": WORK_ORDER, "run_id": run.get("run_id"),
        "properties": run.get("properties") or [],
    })
    COMPARISON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_REPORT.write_text(
        client.redact(render_comparison_markdown(run, summary)),
        encoding="utf-8")
    return {"summary": str(SUMMARY_REPORT), "properties": str(PROPERTY_REPORT),
            "comparison": str(COMPARISON_REPORT)}


# --------------------------------------------------------------------------- #
# Entry point.
# --------------------------------------------------------------------------- #

def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None,
                        help="run identifier (default: a UTC timestamp)")
    parser.add_argument("--only", action="append", default=None,
                        help="restrict to one slug; repeatable. Narrowing is "
                             "allowed for debugging; widening is not.")
    parser.add_argument("--raw-root", default=str(RAW_ROOT))
    parser.add_argument("--no-reports", action="store_true",
                        help="run without writing the committed reports")
    args = parser.parse_args(argv)

    if not client.credential_present():
        print("ERROR: %s is not set." % client.AUTH_ENV, file=sys.stderr)
        return 2

    targets = build_targets()
    if args.only:
        wanted = set(args.only)
        unknown = sorted(wanted - {t.slug for t in targets})
        if unknown:
            print("ERROR: unknown slug(s) %s" % unknown, file=sys.stderr)
            return 2
        targets = tuple(t for t in targets if t.slug in wanted)

    run_id = args.run_id or default_run_id()
    run = asyncio.run(run_pilot(run_id=run_id, targets=targets,
                                raw_root=Path(args.raw_root)))
    summary = summarize(run)

    if not args.no_reports:
        paths = write_reports(run, summary)
        for label, path in paths.items():
            print("wrote %s -> %s" % (label, path))

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("contract_integration_gaps",
                                   "brightdata_reported")}, indent=2))
    return 0


__all__ = [
    "WORK_ORDER", "PILOT_ID", "BRAND", "PILOT_SIZE", "MARKET_ID",
    "TARGET_SPECS", "BENCHMARK", "CRITICAL_FIELDS", "MATCH", "MISMATCH",
    "CAPTURE_ABSENT", "BENCHMARK_SILENT", "CLAUDE_FALLBACK_REQUIRED",
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "HOLD",
    "PilotError", "build_targets", "compare_to_benchmark",
    "build_observation", "evaluate_with_existing_contracts",
    "disposition_for", "run_pilot", "summarize", "write_reports",
    "render_comparison_markdown", "default_run_id", "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
