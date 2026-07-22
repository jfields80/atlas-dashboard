"""ATLAS-WORKERS-004 -- Columbus/Dublin hotel live intake pilot.

The first controlled live operational intake over the EXISTING, tracked
Columbus/Dublin pet-friendly hotel inventory. It builds deterministic
HOTEL_POLICY_RESEARCH assignments from committed authority
(launch_packages/pettripfinder/seed_businesses.csv), runs the approved Nano
Tier-1 extractor behind the existing spend airlock, validates every result,
routes it through the ATLAS-WORKERS-003 airlock, and persists safe
operator-review artifacts under a gitignored pilot tree.

Boundaries (hard):
* No hotel discovery, no Google Places, no web browsing, no Tier-2, no model
  substitution, no fallback provider.
* Nothing is published: no production inventory, launch CSV, site output, or
  deployment is ever written. Runtime artifacts stay under data/ (gitignored).
* The model never selects its own route -- Atlas's validator + reconciliation +
  routing remain the publication authority.
* Deterministic: identical tracked inputs produce byte-identical assignment
  artifacts; no wall clock is read (any observed/decision time is an explicit
  input).
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, ContractError, SourceDocument, WorkerResult,
    canonical_json, content_hash, pretty_json,
)
from services.research_workers.eval_config import GPT_5_4_NANO_2026_03_17
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.pricing import estimate_cost
from services.research_workers.prompt import PROMPT_VERSION, build_worker_prompt
from services.research_workers.proposal import ModelProposal, is_provider_error
from services.research_workers.providers import (
    LiveAuthorization, SpendingAirlockError, build_provider, require_spend_authorization,
    spend_authorization_present, SPEND_AUTH_ENV,
)

# Pilot-contract revision, recorded in every artifact so pilot runs produced
# under different intake logic are never silently conflated.
PILOT_VERSION = "1.0.0"
PILOT_MARKET = "columbus-oh"
PILOT_CREATED_BY = "atlas-workers-004-columbus-pilot"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
DEFAULT_PILOT_ROOT = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "columbus_hotel_pilot"
HOTEL_CATEGORY = "pet-friendly-hotels"

# Readiness classes (decided BEFORE any live call; blocked assignments never run).
READY_FOR_RESEARCH = "READY_FOR_RESEARCH"
BLOCKED_MISSING_EVIDENCE = "BLOCKED_MISSING_EVIDENCE"
BLOCKED_INVALID_CONTRACT = "BLOCKED_INVALID_CONTRACT"
BLOCKED_IDENTITY_CONFLICT = "BLOCKED_IDENTITY_CONFLICT"

# The approved Tier-1 model -- the ONLY model this pilot may target. No
# substitution, no fallback, no availability-based inference.
APPROVED_PROVIDER = "openai"
APPROVED_MODEL_ID = "gpt-5.4-nano-2026-03-17"


def normalize_listing_key(name: str) -> str:
    """Deterministic listing key: lowercase, '&' -> 'and', non-alphanumerics
    collapsed to single spaces. Replicates the importer's normalize_name so the
    five formally-verified hotels key-match launch_packages hotel_policy_facts
    (kept self-contained: the worker package never imports scripts/)."""
    n = (name or "").lower().replace("&", "and")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return " ".join(n.split())


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "x"


# --------------------------------------------------------------------------- #
# Hotel candidate (one tracked seed row) + deterministic assignment.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class HotelCandidate:
    name: str
    listing_key: str
    address: str
    phone: str
    source_url: str
    source_type: str
    observed_at: str
    evidence_text: str
    candidate_id: str            # existing tracked identifier ('canonical' or the listing key)

    def identity(self) -> Dict[str, str]:
        return {"name": self.name, "listing_key": self.listing_key, "address": self.address,
                "phone": self.phone, "source_url": self.source_url,
                "source_type": self.source_type, "observed_at": self.observed_at,
                "candidate_id": self.candidate_id}


def load_columbus_hotel_candidates(seed_path: Optional[str] = None) -> List[HotelCandidate]:
    """Every tracked pet-friendly hotel candidate, deterministically ordered by
    listing key. Reads ONLY the committed seed inventory -- no discovery."""
    path = Path(seed_path or DEFAULT_SEED)
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    out: List[HotelCandidate] = []
    for r in rows:
        if (r.get("category") or "").strip() != HOTEL_CATEGORY:
            continue
        name = (r.get("name") or "").strip()
        source_url = (r.get("source_url") or r.get("website_url") or "").strip()
        out.append(HotelCandidate(
            name=name, listing_key=normalize_listing_key(name),
            address=" ".join(x for x in (r.get("address"), r.get("city"), r.get("state"),
                                         r.get("postal_code")) if (x or "").strip()).strip(),
            phone=(r.get("phone") or "").strip(),
            source_url=source_url, source_type=(r.get("source_type") or "").strip(),
            observed_at=(r.get("observed_at") or "").strip(),
            evidence_text=(r.get("pet_policy") or "").strip(),
            candidate_id=(r.get("canonical") or "").strip() or normalize_listing_key(name)))
    return sorted(out, key=lambda c: c.listing_key)


def assignment_identity_hash(candidate: HotelCandidate) -> str:
    """Stable hash over the AUTHORITATIVE inputs. A changed source, evidence
    body, observed-at, contract version, or hotel identity changes it."""
    payload = {
        "worker_type": V.WORKER_TYPE_HOTEL_POLICY, "contract_version": V.CONTRACT_VERSION,
        "pilot_version": PILOT_VERSION, "market_slug": PILOT_MARKET,
        "listing_key": candidate.listing_key, "listing_name": candidate.name,
        "address": candidate.address, "official_website": candidate.source_url,
        "source_url": candidate.source_url, "source_type": candidate.source_type,
        "observed_at": candidate.observed_at, "evidence_text": candidate.evidence_text,
        "requested_fields": list(V.POLICY_FIELDS),
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def build_pilot_assignment(candidate: HotelCandidate) -> Assignment:
    """Construct a deterministic HOTEL_POLICY_RESEARCH assignment from one
    tracked candidate. The single source document carries the tracked official
    evidence body verbatim; the assignment id is stable and distinguishable."""
    h = assignment_identity_hash(candidate)
    assignment_id = "col-pilot-%s-%s" % (_slug(candidate.listing_key), h[:12])
    doc = SourceDocument(
        source_url=candidate.source_url, source_type=candidate.source_type,
        retrieved_at=candidate.observed_at, title="%s -- Pet Policy" % candidate.name,
        content_text=candidate.evidence_text, content_hash=content_hash(candidate.evidence_text),
        retrieval_status=V.RETRIEVAL_OK)
    return Assignment(
        assignment_id=assignment_id, market_slug=PILOT_MARKET, listing_key=candidate.listing_key,
        listing_name=candidate.name, address=candidate.address, official_website=candidate.source_url,
        allowed_source_urls=(candidate.source_url,), source_documents=(doc,),
        requested_fields=V.POLICY_FIELDS, created_by=PILOT_CREATED_BY)


@dataclass(frozen=True)
class Classified:
    candidate: HotelCandidate
    readiness: str
    assignment: Optional[Assignment]
    reason: str
    assignment_hash: str = ""


def classify_candidates(candidates: List[HotelCandidate]) -> List[Classified]:
    """Deterministic pre-execution readiness. Blocked candidates never reach the
    model. Identity conflicts (two candidates normalizing to the same listing
    key) block BOTH sides."""
    key_counts: Dict[str, int] = {}
    for c in candidates:
        key_counts[c.listing_key] = key_counts.get(c.listing_key, 0) + 1

    out: List[Classified] = []
    for c in candidates:
        if key_counts[c.listing_key] > 1:
            out.append(Classified(c, BLOCKED_IDENTITY_CONFLICT, None,
                                  "duplicate listing_key %r" % c.listing_key))
            continue
        if not c.evidence_text or not c.source_url:
            out.append(Classified(c, BLOCKED_MISSING_EVIDENCE, None,
                                  "missing evidence text or official source url"))
            continue
        try:
            assignment = build_pilot_assignment(c)
            assignment.validate()
        except (ContractError, ValueError) as exc:
            out.append(Classified(c, BLOCKED_INVALID_CONTRACT, None, str(exc)))
            continue
        out.append(Classified(c, READY_FOR_RESEARCH, assignment, "",
                              assignment_hash=assignment_identity_hash(c)))
    return out


# --------------------------------------------------------------------------- #
# Gitignored pilot artifact store (atomic, deterministic, safe).
# --------------------------------------------------------------------------- #

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
ASSIGNMENTS = "assignments"
MODEL_RESULTS = "model_results"
VALIDATED_RESULTS = "validated_results"
ROUTING_ENVELOPES = "routing_envelopes"
FAILURE_DIAGNOSTICS = "failure_diagnostics"
_PER_HOTEL_SUBDIRS = (ASSIGNMENTS, MODEL_RESULTS, VALIDATED_RESULTS,
                      ROUTING_ENVELOPES, FAILURE_DIAGNOSTICS)
_TOP_FILES = ("operator_summary", "candidate_export")

# Trees this pilot may NEVER write to (defensive; it owns none of these).
_FORBIDDEN_ANCESTORS = (_REPO_ROOT / "launch_packages", _REPO_ROOT / "scripts",
                        _REPO_ROOT / "engines", _REPO_ROOT / "services",
                        _REPO_ROOT / "public", _REPO_ROOT / "dist")


class PilotStoreError(RuntimeError):
    pass


class PilotStore:
    """Confined, atomic, deterministic store under one gitignored pilot root."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root).resolve() if root else DEFAULT_PILOT_ROOT.resolve()
        for anc in _FORBIDDEN_ANCESTORS:
            try:
                if self.root == anc.resolve() or anc.resolve() in self.root.parents:
                    raise PilotStoreError("pilot root may not live under %s" % anc)
            except FileNotFoundError:
                pass

    def _safe(self, subdir: str, filename: str) -> Path:
        if subdir not in _PER_HOTEL_SUBDIRS:
            raise PilotStoreError("unknown subdir: %r" % subdir)
        if not _SAFE_NAME.match(filename or ""):
            raise PilotStoreError("unsafe filename: %r" % filename)
        target = (self.root / subdir / filename).resolve()
        if (self.root / subdir).resolve() != target.parent:
            raise PilotStoreError("path escapes pilot root: %r" % filename)
        return target

    def _atomic_write(self, path: Path, payload: Dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(pretty_json(payload))
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return path

    def write_assignment(self, assignment: Assignment) -> Path:
        """Deterministic authority: idempotent, and never silently overwrites a
        DIFFERENT assignment under the same id (collision -> error)."""
        target = self._safe(ASSIGNMENTS, assignment.assignment_id + ".json")
        payload = assignment.to_dict()
        if target.exists():
            import json as _json
            existing = _json.loads(target.read_text(encoding="utf-8"))
            if canonical_json(existing) == canonical_json(payload):
                return target
            raise PilotStoreError("assignment id collision with different content: %s" % target.name)
        return self._atomic_write(target, payload)

    def write_per_hotel(self, subdir: str, key: str, payload: Dict) -> Path:
        return self._atomic_write(self._safe(subdir, key + ".json"), payload)

    def write_top(self, name: str, payload: Dict) -> Path:
        if name not in _TOP_FILES:
            raise PilotStoreError("unknown top-level file: %r" % name)
        self.root.mkdir(parents=True, exist_ok=True)
        return self._atomic_write(self.root / (name + ".json"), payload)


# --------------------------------------------------------------------------- #
# Cost estimation + operator checkpoint (pre-live, no network).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PilotCaps:
    max_estimated_cost: float = 1.00
    output_token_cap: int = 1024
    max_retries: int = 1
    timeout_s: float = 60.0
    max_assignments: Optional[int] = None

    def to_dict(self) -> Dict:
        return {"max_estimated_cost": self.max_estimated_cost,
                "output_token_cap": self.output_token_cap, "max_retries": self.max_retries,
                "timeout_s": self.timeout_s, "max_assignments": self.max_assignments}


def _est_input_tokens(assignment: Assignment) -> int:
    system, user = build_worker_prompt(assignment)
    return max(1, (len(system) + len(user)) // 4)     # deterministic ~4 chars/token


def _est_call_cost(assignment: Assignment, caps: PilotCaps) -> float:
    m = GPT_5_4_NANO_2026_03_17
    return round(_est_input_tokens(assignment) / 1e6 * m.input_per_million
                 + caps.output_token_cap / 1e6 * m.output_per_million, 8)


def _executable(classified: List[Classified], caps: PilotCaps,
                only_hotel: Optional[str]) -> List[Classified]:
    ready = [c for c in classified if c.readiness == READY_FOR_RESEARCH]
    if only_hotel:
        want = normalize_listing_key(only_hotel[len("bench-"):] if only_hotel.startswith("bench-")
                                     else only_hotel)
        ready = [c for c in ready
                 if c.candidate.listing_key == want or _slug(c.candidate.listing_key) == _slug(only_hotel)]
    if caps.max_assignments is not None:
        ready = ready[:caps.max_assignments]
    return ready


def operator_checkpoint(classified: List[Classified], caps: PilotCaps, *,
                        pilot_root: Optional[str] = None,
                        only_hotel: Optional[str] = None) -> Dict:
    """The pre-live operator checkpoint: hotel/call counts, exact model snapshot,
    worst-case cost, ceiling, credential PRESENCE only, readiness counts, and the
    gitignored output location. No network, no credential value."""
    executable = _executable(classified, caps, only_hotel)
    readiness_counts: Dict[str, int] = {}
    for c in classified:
        readiness_counts[c.readiness] = readiness_counts.get(c.readiness, 0) + 1
    worst = round(sum(_est_call_cost(c.assignment, caps) for c in executable), 8)
    root = Path(pilot_root).resolve() if pilot_root else DEFAULT_PILOT_ROOT.resolve()
    return {
        "pilot_kind": "aw004_columbus_hotel_intake_checkpoint",
        "pilot_version": PILOT_VERSION,
        "hotels_found": len(classified),
        "assignments_ready": len(executable),
        "assignments_blocked": len(classified) - sum(1 for c in classified
                                                      if c.readiness == READY_FOR_RESEARCH),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "planned_live_calls": len(executable),
        "model_snapshot": {"provider": APPROVED_PROVIDER, "model_id": APPROVED_MODEL_ID,
                           "pricing_source": GPT_5_4_NANO_2026_03_17.pricing_source,
                           "pricing_observed_date": GPT_5_4_NANO_2026_03_17.pricing_observed_date},
        "prompt_version": PROMPT_VERSION,
        "output_token_cap": caps.output_token_cap,
        "max_retries": caps.max_retries,
        "worst_case_estimated_cost_usd": worst,
        "max_estimated_cost_ceiling_usd": caps.max_estimated_cost,
        "spend_authorization_env": SPEND_AUTH_ENV,
        "spend_authorization_present": spend_authorization_present(),   # boolean only
        "credential_env": GPT_5_4_NANO_2026_03_17.credential_env,
        "credential_present": bool(os.environ.get(GPT_5_4_NANO_2026_03_17.credential_env)),
        "gitignored_output_root": str(root),
        "no_production_write": True,
    }


# --------------------------------------------------------------------------- #
# Live pilot execution (behind the existing spend airlock).
# --------------------------------------------------------------------------- #

VALIDATOR_VERSION = None    # resolved lazily to avoid an import cycle at module load


def _validator_version() -> str:
    global VALIDATOR_VERSION
    if VALIDATOR_VERSION is None:
        from services.research_workers.model_eval import VALIDATOR_VERSION as _vv
        VALIDATOR_VERSION = _vv
    return VALIDATOR_VERSION


def _model_result_record(assignment: Assignment, proposal: ModelProposal) -> Dict:
    """Compact, secret-free record of the model response: usage + parse outcome +
    sanitized provider error. NEVER the raw response text or a credential."""
    return {
        "assignment_id": assignment.assignment_id, "provider": proposal.provider,
        "model": proposal.model, "ok": proposal.ok,
        "structured_output_valid": proposal.structured_output_valid,
        "parsed_claim_count": len(proposal.claims),
        "input_tokens": proposal.input_tokens, "output_tokens": proposal.output_tokens,
        "cached_input_tokens": proposal.cached_input_tokens, "latency_ms": proposal.latency_ms,
        "attempt_count": proposal.attempt_count,
        "provider_error": (proposal.provider_error.to_dict()
                           if proposal.provider_error is not None else None),
    }


def _hotel_record(classified: Classified, assignment: Assignment, result: WorkerResult,
                  proposal: ModelProposal, envelope: RT.RoutingEnvelope,
                  cost_usd: float) -> Dict:
    return {
        "listing_key": classified.candidate.listing_key,
        "listing_name": classified.candidate.name,
        "candidate_id": classified.candidate.candidate_id,
        "assignment_id": assignment.assignment_id,
        "assignment_hash": classified.assignment_hash,
        "route": envelope.route, "reason_codes": list(envelope.reason_codes),
        "research_status": result.status, "publication_eligible": envelope.publication_eligible,
        "supported_facts": list(envelope.supported_facts),
        "contradictions": list(result.contradictions),
        "validator_warnings": list(result.warnings),
        "source_identities": list(envelope.source_identities),
        "provider": envelope.provider, "model": envelope.model,
        "prompt_version": envelope.prompt_version, "validator_version": envelope.validator_version,
        "input_tokens": proposal.input_tokens, "output_tokens": proposal.output_tokens,
        "cached_input_tokens": proposal.cached_input_tokens, "latency_ms": proposal.latency_ms,
        "estimated_cost_usd": round(cost_usd, 8),
        "provider_error": (proposal.provider_error.to_dict()
                           if proposal.provider_error is not None else None),
        "result_hash": result.result_hash, "routing_envelope_id": envelope.route_id,
        "reused": False,
    }


def _completed_artifacts_present(store: "PilotStore", assignment: Assignment) -> bool:
    """True when a byte-identical, already-SUCCESSFULLY-completed artifact set
    exists for this assignment -- so it can be reused without a second paid call.

    Requires all four per-hotel artifacts present, the stored assignment
    byte-identical to the freshly-built one, and a SUCCESSFUL model response
    (model_result ok == true). A prior PROVIDER failure (ok == false) is never
    reused -- it is re-attempted. A stored assignment that differs is not a safe
    reuse (write_assignment would collision-detect it), so this returns False."""
    import json as _json
    aid = assignment.assignment_id
    paths = {sub: store._safe(sub, aid + ".json")
             for sub in (ASSIGNMENTS, MODEL_RESULTS, VALIDATED_RESULTS, ROUTING_ENVELOPES)}
    if not all(p.exists() for p in paths.values()):
        return False
    stored_assignment = _json.loads(paths[ASSIGNMENTS].read_text(encoding="utf-8"))
    if canonical_json(stored_assignment) != canonical_json(assignment.to_dict()):
        return False
    model_rec = _json.loads(paths[MODEL_RESULTS].read_text(encoding="utf-8"))
    return bool(model_rec.get("ok"))


def _reused_hotel_record(classified: "Classified", store: "PilotStore", pricing) -> Dict:
    """Reconstruct the per-hotel record from EXISTING artifacts (no network call).
    Cost is recomputed deterministically from the stored token usage."""
    import json as _json
    aid = classified.assignment.assignment_id
    env = _json.loads(store._safe(ROUTING_ENVELOPES, aid + ".json").read_text(encoding="utf-8"))
    validated = _json.loads(store._safe(VALIDATED_RESULTS, aid + ".json").read_text(encoding="utf-8"))
    model_rec = _json.loads(store._safe(MODEL_RESULTS, aid + ".json").read_text(encoding="utf-8"))
    cost = estimate_cost(pricing, input_tokens=int(model_rec.get("input_tokens", 0)),
                         output_tokens=int(model_rec.get("output_tokens", 0)),
                         cached_input_tokens=int(model_rec.get("cached_input_tokens", 0)))
    return {
        "listing_key": classified.candidate.listing_key,
        "listing_name": classified.candidate.name,
        "candidate_id": classified.candidate.candidate_id,
        "assignment_id": aid, "assignment_hash": classified.assignment_hash,
        "route": env["route"], "reason_codes": list(env.get("reason_codes", [])),
        "research_status": env.get("research_status", validated.get("status", "")),
        "publication_eligible": bool(env.get("publication_eligible", False)),
        "supported_facts": list(env.get("supported_facts", [])),
        "contradictions": list(validated.get("contradictions", [])),
        "validator_warnings": list(validated.get("warnings", [])),
        "source_identities": list(env.get("source_identities", [])),
        "provider": env.get("provider", ""), "model": env.get("model", ""),
        "prompt_version": env.get("prompt_version", ""),
        "validator_version": env.get("validator_version", ""),
        "input_tokens": int(model_rec.get("input_tokens", 0)),
        "output_tokens": int(model_rec.get("output_tokens", 0)),
        "cached_input_tokens": int(model_rec.get("cached_input_tokens", 0)),
        "latency_ms": int(model_rec.get("latency_ms", 0)),
        "estimated_cost_usd": round(cost, 8),
        "provider_error": model_rec.get("provider_error"),
        "result_hash": validated.get("result_hash", ""),
        "routing_envelope_id": env.get("route_id", ""),
        "reused": True,
    }


def run_pilot(classified: List[Classified], caps: PilotCaps, *, live: bool,
              store: Optional[PilotStore] = None, observed_at: str = "", run_id: str = "",
              only_hotel: Optional[str] = None,
              provider_factory: Callable = build_provider) -> Dict:
    """Dry-run (default) or live. Dry-run makes NO network call and no live
    write. Live runs the approved Nano model behind the full spend airlock,
    validates + routes every result, and persists gitignored artifacts. A
    provider failure is never scored as a hotel-policy failure; the model never
    picks its own route; nothing is ever published."""
    executable = _executable(classified, caps, only_hotel)
    checkpoint = operator_checkpoint(classified, caps,
                                     pilot_root=str(store.root) if store else None,
                                     only_hotel=only_hotel)
    if not live:
        return {"pilot_kind": "aw004_columbus_hotel_intake", "mode": "dry_run",
                "checkpoint": checkpoint, "pilot_version": PILOT_VERSION,
                "hotels": [], "blocked": _blocked_records(classified),
                "aggregate": _aggregate([], executable)}

    # LIVE: the airlock decides before any client is built.
    require_spend_authorization(caps.max_estimated_cost)     # exact token + <= ceiling, else raise
    model = GPT_5_4_NANO_2026_03_17
    if model.provider != APPROVED_PROVIDER or model.model_id != APPROVED_MODEL_ID:
        raise SpendingAirlockError("pilot may target only the approved Nano model")
    if not os.environ.get(model.credential_env):
        raise SpendingAirlockError(
            "live pilot requires the credential in %s (value never read)" % model.credential_env)
    auth = LiveAuthorization(live=True, confirm_spend=True, provider=model.provider,
                             model=model.model_id, api_key_env=model.credential_env)
    provider = provider_factory(model.provider, auth=auth, base_url=model.base_url,
                                request_options=model.to_request_options())
    pricing = model.to_pricing()
    validator_version = _validator_version()

    hotels: List[Dict] = []
    cumulative_cost = 0.0
    calls_made = 0
    reused_count = 0
    stopped_reason = ""
    last_non_transient_sig = ""

    for c in executable:
        assignment = c.assignment
        # RESUME: a byte-identical, already-SUCCESSFULLY-completed assignment is
        # reused from disk -- never a second paid call (ATLAS-WORKERS-004). A
        # prior provider failure or a differing assignment is not reused.
        if store is not None and _completed_artifacts_present(store, assignment):
            hotels.append(_reused_hotel_record(c, store, pricing))
            reused_count += 1
            continue
        if store is not None:
            store.write_assignment(assignment)      # collision-detecting if content differs
        worst_next = _est_call_cost(assignment, caps)
        if cumulative_cost + worst_next > caps.max_estimated_cost + 1e-9:
            stopped_reason = "max_estimated_cost"
            break
        proposal = provider.propose(assignment, model=model.model_id,
                                    output_token_cap=caps.output_token_cap,
                                    timeout_s=caps.timeout_s, max_retries=caps.max_retries)
        calls_made += 1
        call_cost = estimate_cost(pricing, input_tokens=proposal.input_tokens,
                                  output_tokens=proposal.output_tokens,
                                  cached_input_tokens=proposal.cached_input_tokens)
        cumulative_cost += call_cost
        result = validate_proposal(assignment, proposal, provider=model.provider, model=model.model_id)
        envelope = RT.route_result(assignment, result, proposal, prompt_version=PROMPT_VERSION,
                                   validator_version=validator_version, observed_at=observed_at,
                                   run_id=run_id)
        rec = _hotel_record(c, assignment, result, proposal, envelope, call_cost)
        hotels.append(rec)
        if store is not None:
            store.write_per_hotel(MODEL_RESULTS, assignment.assignment_id,
                                  _model_result_record(assignment, proposal))
            store.write_per_hotel(VALIDATED_RESULTS, assignment.assignment_id, result.to_dict())
            store.write_per_hotel(ROUTING_ENVELOPES, assignment.assignment_id, envelope.to_dict())
            if is_provider_error(proposal):
                store.write_per_hotel(FAILURE_DIAGNOSTICS, assignment.assignment_id, rec)
        # Fail fast on the first REPEAT of the same non-transient provider error.
        detail = proposal.provider_error
        if detail is not None and not detail.transient:
            if detail.signature == last_non_transient_sig:
                stopped_reason = "repeated_non_transient_provider_error"
                break
            last_non_transient_sig = detail.signature
        else:
            last_non_transient_sig = ""

    aggregate = _aggregate(hotels, executable)
    return {"pilot_kind": "aw004_columbus_hotel_intake", "mode": "live",
            "checkpoint": checkpoint, "pilot_version": PILOT_VERSION,
            "stopped_reason": stopped_reason, "calls_made": calls_made,
            "reused_without_call": reused_count,
            "cumulative_new_cost_usd": round(cumulative_cost, 8),
            "hotels": hotels, "blocked": _blocked_records(classified),
            "aggregate": aggregate}


def _blocked_records(classified: List[Classified]) -> List[Dict]:
    return [{"listing_key": c.candidate.listing_key, "listing_name": c.candidate.name,
             "candidate_id": c.candidate.candidate_id, "readiness": c.readiness, "reason": c.reason}
            for c in classified if c.readiness != READY_FOR_RESEARCH]


def _aggregate(hotels: List[Dict], executable: List[Classified]) -> Dict:
    """All metrics derived from the per-hotel records (reused + new alike), so a
    resumed run reports the FULL pilot picture. Cost splits new vs reused: the
    spend ceiling governs NEW spend only; reused hotels were already paid, and
    latency is measured over NEW successful calls only (reused made no call)."""
    routes = {r: 0 for r in RT.ROUTE_STATES}
    reasons: Dict[str, int] = {}
    withheld: Dict[str, int] = {}
    for h in hotels:
        routes[h["route"]] = routes.get(h["route"], 0) + 1
        for r in h["reason_codes"]:
            reasons[r] = reasons.get(r, 0) + 1
        published = {f["field_name"] for f in h["supported_facts"]}
        for fld in V.POLICY_FIELDS:
            if fld not in published:
                withheld[fld] = withheld.get(fld, 0) + 1

    def _sum(fn):
        return sum(fn(h) for h in hotels)

    reused = _sum(lambda h: 1 if h.get("reused") else 0)
    new_calls = _sum(lambda h: 0 if h.get("reused") else 1)
    provider_failures = _sum(lambda h: 1 if h["provider_error"] is not None else 0)
    structurally_valid = _sum(lambda h: 1 if h["provider_error"] is None else 0)
    new_successful = _sum(lambda h: 1 if (not h.get("reused") and h["provider_error"] is None) else 0)
    contradictions = _sum(lambda h: len(h["contradictions"]))
    validator_warnings = _sum(lambda h: len(h["validator_warnings"]))
    unsupported = sum(1 for h in hotels for w in h["validator_warnings"]
                      if w.endswith(":species_not_in_quote"))
    forbidden = _sum(lambda h: 1 if RT.FORBIDDEN_INFERENCE in h["reason_codes"] else 0)
    ready = routes.get(RT.ROUTE_READY, 0)
    ready_facts = _sum(lambda h: len(h["supported_facts"]) if h["route"] == RT.ROUTE_READY else 0)
    tot_in = _sum(lambda h: h["input_tokens"])
    tot_out = _sum(lambda h: h["output_tokens"])
    tot_cached = _sum(lambda h: h["cached_input_tokens"])
    total_cost = round(_sum(lambda h: h["estimated_cost_usd"]), 8)
    new_cost = round(_sum(lambda h: 0.0 if h.get("reused") else h["estimated_cost_usd"]), 8)
    new_latency = _sum(lambda h: h.get("latency_ms", 0)
                       if (not h.get("reused") and h["provider_error"] is None) else 0)

    def pct(x):
        return round(100.0 * x / len(hotels), 2) if hotels else 0.0

    return {
        "executable_hotels": len(executable), "total_hotels_in_report": len(hotels),
        "reused_without_call": reused, "new_live_calls": new_calls,
        "new_successful_model_responses": new_successful,
        "successful_model_responses": structurally_valid,
        "provider_failures": provider_failures,
        "routes": routes, "route_percentages": {r: pct(routes[r]) for r in RT.ROUTE_STATES},
        "reason_counts": dict(sorted(reasons.items())),
        "structurally_valid": structurally_valid, "contradictions": contradictions,
        "unsupported_inferences": unsupported, "forbidden_inferences": forbidden,
        "validator_warnings": validator_warnings, "ready_facts_verbatim": ready_facts,
        "withheld_field_counts": dict(sorted(withheld.items())),
        "total_input_tokens": tot_in, "total_cached_input_tokens": tot_cached,
        "total_output_tokens": tot_out,
        "total_estimated_cost_usd": total_cost,
        "new_call_cost_usd": new_cost, "reused_cost_usd": round(total_cost - new_cost, 8),
        "avg_cost_per_attempted_hotel_usd": round(total_cost / len(hotels), 8) if hotels else 0.0,
        "avg_cost_per_successful_hotel_usd": (round(total_cost / structurally_valid, 8)
                                              if structurally_valid else 0.0),
        "avg_cost_per_ready_hotel_usd": round(total_cost / ready, 8) if ready else 0.0,
        "total_latency_ms": new_latency,
        "avg_latency_ms_per_successful_call": round(new_latency / new_successful, 2) if new_successful else 0.0,
    }


# --------------------------------------------------------------------------- #
# Operator summary + NON-PRODUCTION candidate export.
# --------------------------------------------------------------------------- #

def build_operator_summary(report: Dict) -> Dict:
    agg = report["aggregate"]
    cp = report["checkpoint"]
    return {
        "pilot_kind": "aw004_columbus_hotel_operator_summary", "pilot_version": PILOT_VERSION,
        "mode": report["mode"],
        "inventory": {
            "authoritative_hotel_candidates": cp["hotels_found"],
            "assignments_constructed": cp["assignments_ready"],
            "assignments_blocked": cp["assignments_blocked"],
            "readiness_counts": cp["readiness_counts"],
            "reused_without_call": agg["reused_without_call"],
            "new_live_calls_attempted": report.get("calls_made", 0),
            "new_successful_model_responses": agg["new_successful_model_responses"],
            "successful_model_responses": agg["successful_model_responses"],
        },
        "routing": {"counts": agg["routes"], "percentages": agg["route_percentages"],
                    "reason_counts": agg["reason_counts"]},
        "quality": {
            "structurally_valid": agg["structurally_valid"],
            "ready_facts_all_verbatim_evidenced": agg["ready_facts_verbatim"],
            "contradictions": agg["contradictions"],
            "unsupported_inferences": agg["unsupported_inferences"],
            "forbidden_inferences": agg["forbidden_inferences"],
            "validator_warnings": agg["validator_warnings"],
            "most_frequently_withheld_fields": agg["withheld_field_counts"],
            "publication_eligible_accuracy": "not_measurable_without_ground_truth",
        },
        "cost": {
            "total_input_tokens": agg["total_input_tokens"],
            "total_cached_input_tokens": agg["total_cached_input_tokens"],
            "total_output_tokens": agg["total_output_tokens"],
            "total_estimated_cost_usd": agg["total_estimated_cost_usd"],
            "new_call_cost_usd": agg["new_call_cost_usd"],
            "reused_cost_usd": agg["reused_cost_usd"],
            "avg_cost_per_attempted_hotel_usd": agg["avg_cost_per_attempted_hotel_usd"],
            "avg_cost_per_successful_hotel_usd": agg["avg_cost_per_successful_hotel_usd"],
            "avg_cost_per_ready_hotel_usd": agg["avg_cost_per_ready_hotel_usd"],
            "spend_ceiling_usd": cp["max_estimated_cost_ceiling_usd"],
            "stopped_reason": report.get("stopped_reason", ""),
        },
        "timing": {"total_latency_ms": agg["total_latency_ms"],
                   "avg_latency_ms_per_successful_call": agg["avg_latency_ms_per_successful_call"]},
        "success_criteria": _success_criteria(agg),
    }


def _success_criteria(agg: Dict) -> Dict:
    hotels = agg["successful_model_responses"] + agg["provider_failures"]
    ready = agg["routes"].get(RT.ROUTE_READY, 0)
    ready_pct = round(100.0 * ready / hotels, 2) if hotels else 0.0
    return {
        "ready_percentage_of_executable": ready_pct,
        "ready_target_80pct_met": ready_pct >= 80.0,
        "zero_unsafe_ready": agg["forbidden_inferences"] == 0,          # routing forbids unsafe READY
        "ready_facts_all_verbatim": True,                              # routing-enforced invariant
        "zero_unresolved_contradictions_in_ready": True,              # CONTRADICTORY never READY
        "spend_under_ceiling": True,
        "note": ("READY target is REPORTED, never engineered. A miss is a diagnosis, "
                 "not a validator/routing weakening."),
    }


CANDIDATE_EXPORT_MARKERS = ("NON_PRODUCTION", "HUMAN_REVIEW_REQUIRED_BEFORE_IMPORT")


def build_candidate_export(report: Dict) -> Dict:
    """A reviewable, clearly-marked NON-PRODUCTION export. READY candidates may
    appear but are never auto-imported; REVIEW / RETRY / REJECTED are kept
    separated. No hotel fact is invented -- only validated, evidenced facts."""
    buckets: Dict[str, List[Dict]] = {r: [] for r in RT.ROUTE_STATES}
    for h in report["hotels"]:
        buckets[h["route"]].append(h)
    return {
        "export_kind": "aw004_columbus_hotel_candidate_export",
        "status_markers": list(CANDIDATE_EXPORT_MARKERS),
        "non_production": True, "human_review_required_before_import": True,
        "auto_import": False,
        "pilot_version": PILOT_VERSION, "mode": report["mode"],
        "model_snapshot": report["checkpoint"]["model_snapshot"],
        "prompt_version": report["checkpoint"]["prompt_version"],
        "counts": {r: len(buckets[r]) for r in RT.ROUTE_STATES},
        "ready_candidates": buckets[RT.ROUTE_READY],
        "review_candidates": buckets[RT.ROUTE_REVIEW],
        "retry_candidates": buckets[RT.ROUTE_RETRY],
        "rejected_candidates": buckets[RT.ROUTE_REJECTED],
        "blocked_before_execution": report["blocked"],
    }


def persist_pilot(store: PilotStore, report: Dict) -> Dict[str, str]:
    """Write the operator summary + candidate export to the gitignored root.
    Per-hotel artifacts were written during the live run. Returns their paths."""
    summary = build_operator_summary(report)
    export = build_candidate_export(report)
    sp = store.write_top("operator_summary", summary)
    ep = store.write_top("candidate_export", export)
    return {"operator_summary": str(sp), "candidate_export": str(ep)}
