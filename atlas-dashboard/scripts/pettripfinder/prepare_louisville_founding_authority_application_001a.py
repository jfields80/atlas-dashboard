"""Prepare, but never execute, Louisville authority application 001A."""
from __future__ import annotations

import json
import hashlib
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, partition, policy_schema

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
R = PKG / "markets" / "reports"
OUT = R / "louisville_founding_authority_application_001a_prepared.json"


def _load(name: str) -> dict:
    return json.loads((R / name).read_text(encoding="utf-8-sig"))


def _approved_row_contracts(positives: list[str], negatives: list[str]) -> list[dict]:
    """Verify every approved decision against its captured first-party artifact.

    This deliberately validates the existing capture packages only.  It does
    not turn a founder decision into authority or reconstruct any policy facts.
    """
    packages = (
        ("pass1", _load("louisville_pass1_founder_decisions.json"),
         _load("louisville_pass1_capture_results.json"),
         REPO / "data" / "operator_evidence" / "louisville-pass1-capture-001"),
        ("pass2", _load("louisville_pass2_founder_decisions.json"),
         _load("louisville_pass2_capture_results.json"),
         REPO / "data" / "operator_evidence" / "louisville-pass2-capture-001"),
        ("pass4", _load("louisville_pass4_founder_decisions.json"),
         _load("louisville_attended_capture_pass4_001.json"),
         REPO / "data" / "operator_evidence" / "louisville-pass4-capture-001"),
    )
    wanted = set(positives) | set(negatives)
    found: dict[str, dict] = {}
    for pass_name, decision_doc, capture_doc, artifact_root in packages:
        decisions = {d["identity_key"]: d for d in decision_doc["decisions"]}
        captured = {r["identity_key"]: r for r in capture_doc["rows"]}
        for key in wanted & decisions.keys():
            decision = decisions[key]
            row = captured.get(key)
            if row is None or row.get("identity_binding") != "BOUND":
                raise SystemExit("%s has no bound captured identity" % key)
            if pass_name == "pass4":
                artifacts = decision.get("artifacts") or []
                if not artifacts:
                    raise SystemExit("%s has no Pass 4 artifacts" % key)
                for artifact in artifacts:
                    path = artifact_root / artifact["relpath"]
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
                        raise SystemExit("%s artifact hash does not resolve" % key)
            else:
                path = artifact_root / str(row.get("artifact_relpath") or "")
                captured_hash = row.get("artifact_sha256")
                if (not path.is_file() or not captured_hash
                        or decision.get("artifact_sha256") != captured_hash
                        or hashlib.sha256(path.read_bytes()).hexdigest() != captured_hash):
                    raise SystemExit("%s artifact hash does not resolve" % key)
            found[key] = OrderedDict((
                ("identity_key", key), ("pass", pass_name),
                ("founder_decision", decision["decision"]),
                ("identity_binding", "BOUND"),
                ("evidence_contract", "CONTRACT_VALID"),
            ))
    if set(found) != wanted:
        raise SystemExit("approved evidence validation missed %s" % sorted(wanted - set(found)))
    return [found[key] for key in positives + negatives]


def main() -> None:
    app = _load("louisville_pass4_decision_application_prepared.json")
    decisions = _load("louisville_pass4_founder_decisions.json")
    p4 = {d["identity_key"]: d for d in decisions["decisions"]}
    for key in ("travelodge by wyndham sellersburg louisville north", "super 8 by wyndham louisville airport"):
        charge = p4[key]["approved_facts"]["other_charges"][0]
        issues = policy_schema.validate_facts({"other_charges": [charge]})
        if issues or charge.get("refundable") is not None or charge.get("trigger") != "if applicable":
            raise SystemExit("conditional sanitation representation invalid for %s: %s" % (key, issues))
    census_doc = json.loads((PKG / "identity_census" / "louisville-ky.json").read_text(encoding="utf-8-sig"))
    part = json.loads((PKG / "louisville_final_partition_001.json").read_text(encoding="utf-8-sig"))
    rec = partition.reconcile(census.identity_keys(census_doc), part, market_id="louisville-ky")
    states = Counter(i["final_state"] for i in part["items"])
    out_of_category = states["OUT_OF_CURRENT_CATEGORY"]
    out_of_category_keys = [i["identity_key"] for i in part["items"]
                            if i["final_state"] == "OUT_OF_CURRENT_CATEGORY"]
    if not rec.agrees or (rec.published, rec.verified_no_pets, rec.unresolved, out_of_category) != (0, 0, 129, 1):
        raise SystemExit("Louisville partition baseline is not 0/0/1/129")
    positives = app["approved_positive_keys"]
    negatives = app["approved_verified_no_pets_keys"]
    if len(positives) != 14 or len(negatives) != 4 or set(positives) & set(negatives):
        raise SystemExit("approved set must be 14 positives plus 4 no-pets")
    approved_rows = _approved_row_contracts(positives, negatives)
    write_json(OUT, OrderedDict((
        ("schema", "ptf-louisville-founding-authority-application-001a-prepared/1.0"),
        ("work_order", "PTF-LOUISVILLE-FOUNDING-AUTHORITY-APPLICATION-001A"),
        ("market_id", "louisville-ky"), ("as_of", "2026-08-17"),
        ("executed", False), ("authority_applied", False),
        ("application_set", OrderedDict((("positives", positives), ("verified_no_pets", negatives)))),
        ("approved_row_contracts", approved_rows),
        ("contract_validation", OrderedDict((("approved_rows_valid", 18),
            ("travelodge_representable", True), ("super8_representable", True),
            ("sanitation_kind", "sanitation_fee"),
            ("refundability_rule", "optional; absent means source-silent and is never false")))),
        ("partition_baseline", OrderedDict((("census", census_doc["count"]),
            ("published", rec.published), ("verified_no_pets", rec.verified_no_pets),
            ("out_of_current_category", out_of_category),
            ("out_of_current_category_keys", out_of_category_keys),
            ("unresolved", rec.unresolved),
            ("other_terminal", 0), ("reconciliation_agrees", rec.agrees),
            ("equation", "130 = 0 published + 0 verified_no_pets + 1 out_of_current_category + 129 unresolved + 0 other_terminal")))),
        ("note", "Prepared only after contract and baseline validation. No authority applied."),
    )))
    print("prepared", 18, "baseline", rec.published, rec.verified_no_pets, out_of_category, rec.unresolved)


if __name__ == "__main__":
    main()
