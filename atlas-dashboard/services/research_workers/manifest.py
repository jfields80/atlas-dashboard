"""ATLAS-WORKERS-001A -- benchmark manifest gates + evidence synchronization.

``verify_evidence_sync`` proves every REAL benchmark case still matches the
exact evidence committed in the tracked launch package
(launch_packages/pettripfinder/hotel_policy_facts.json): the recorded evidence
hash must equal the current committed quote's hash, and that quote must appear
verbatim inside the case's source document. If the launch-package quotation
changes without an intentional benchmark rebuild, this fails loudly.

``validate_manifest`` enforces the composition gates (case count, REAL/synthetic
mix, required adversarial coverage, and the absence of any private operational
path). Both return a list of problem strings -- empty means OK.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from services.research_workers import vocabulary as V

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK = Path(__file__).resolve().parent / "benchmarks" / "hotel_policy_columbus.json"
DEFAULT_FACTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"

CASE_REAL = "REAL"
CASE_SYNTHETIC = "SYNTHETIC_ADVERSARIAL"
_INJECTION_MARKER = "Ignore previous instructions"
# Operational/private path fragments that must NEVER appear in the committed
# benchmark (the tracked launch package IS allowed).
_FORBIDDEN_PATHS = ("data/import", "data\\import", "data/discovery", "data\\discovery",
                    "/candidates/", "\\candidates\\", "run_001")


def _hash(quote: str) -> str:
    return "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()


def _load(path: Optional[str], default: Path) -> Dict:
    return json.loads(Path(path or default).read_text(encoding="utf-8"))


def _facts_by_key(path: Optional[str] = None) -> Dict[str, Dict]:
    return {h["key"]: h for h in _load(path, DEFAULT_FACTS)["hotels"]}


def _doc_texts(case: Dict) -> List[str]:
    return [d.get("content_text", "") for d in case["assignment"].get("source_documents", [])]


def verify_evidence_sync(benchmark_path: Optional[str] = None, facts_path: Optional[str] = None) -> List[str]:
    bench = _load(benchmark_path, DEFAULT_BENCHMARK)
    facts = _facts_by_key(facts_path)
    problems: List[str] = []
    for case in bench["cases"]:
        if case.get("case_kind") != CASE_REAL:
            continue
        prov = case.get("provenance", {})
        key = prov.get("source_record_key", "")
        rec = facts.get(key)
        if rec is None:
            problems.append("%s: source_record_key %r not in launch package" % (case["case_id"], key))
            continue
        committed = rec["evidence_quote"]
        if prov.get("evidence_hash") != _hash(committed):
            problems.append("%s: evidence drift -- launch-package quote changed without a benchmark rebuild"
                            % case["case_id"])
        if not any(committed in t for t in _doc_texts(case)):
            problems.append("%s: committed evidence quote not present verbatim in the case document"
                            % case["case_id"])
        if prov.get("source_package_path") != "launch_packages/pettripfinder/hotel_policy_facts.json":
            problems.append("%s: unexpected source_package_path" % case["case_id"])
    return problems


def validate_manifest(benchmark_path: Optional[str] = None, facts_path: Optional[str] = None) -> List[str]:
    bench = _load(benchmark_path, DEFAULT_BENCHMARK)
    cases = bench["cases"]
    problems: List[str] = []

    if len(cases) != 10:
        problems.append("expected exactly 10 cases, found %d" % len(cases))

    ids = [c["assignment"]["assignment_id"] for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("assignment IDs are not unique")

    reals = [c for c in cases if c.get("case_kind") == CASE_REAL]
    synth = [c for c in cases if c.get("case_kind") == CASE_SYNTHETIC]
    if len(reals) < 6:
        problems.append("at least six REAL cases required, found %d" % len(reals))
    if not synth:
        problems.append("no SYNTHETIC_ADVERSARIAL cases present")
    if len(reals) + len(synth) != len(cases):
        problems.append("every case must be labeled REAL or SYNTHETIC_ADVERSARIAL")

    # REAL cases must sync to the launch package.
    problems.extend(verify_evidence_sync(benchmark_path, facts_path))

    def _has(pred):
        return any(pred(c) for c in cases)

    def _docs(c):
        return c["assignment"].get("source_documents", [])

    def _exp(c):
        return c.get("expected", {})

    if not _has(lambda c: any(_INJECTION_MARKER in d.get("content_text", "") for d in _docs(c))):
        problems.append("no prompt-injection source present")
    if not _has(lambda c: _exp(c).get("status") == V.STATUS_CONTRADICTORY or _exp(c).get("contradiction_fields")):
        problems.append("no contradictory case present")
    if not _has(lambda c: any(d.get("retrieval_status") in (V.RETRIEVAL_BLOCKED, V.RETRIEVAL_NOT_FOUND, V.RETRIEVAL_ERROR)
                              for d in _docs(c)) or _exp(c).get("status") == V.STATUS_NO_OFFICIAL_SOURCE):
        problems.append("no blocked/no-source case present")
    if not _has(lambda c: _exp(c).get("supported", {}).get("pets_allowed") == "true"
                and {"dogs_accepted", "cats_accepted"}.issubset(set(_exp(c).get("forbidden_supported", [])))):
        problems.append("no generic pets-welcome case forbidding dog/cat inference")
    if not _has(lambda c: "fee_basis" in _exp(c).get("supported", {})
                or "refundable_deposit" in _exp(c).get("forbidden_supported", [])):
        problems.append("no fee-basis / fee-deposit distinction case")
    if not _has(lambda c: {"weight_limit", "maximum_pets"} & set(_exp(c).get("forbidden_supported", []))):
        problems.append("no weight/max-pets non-inference case")

    blob = json.dumps(bench, ensure_ascii=False)
    for frag in _FORBIDDEN_PATHS:
        if frag in blob:
            problems.append("private/operational path fragment present in benchmark: %r" % frag)
    return problems
