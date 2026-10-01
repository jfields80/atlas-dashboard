"""PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002 -- the evidence that Austin's source-ready market was refreshed under
the repaired shared first-party reader, and that the package sealed before the repair is historical only.

    python -m scripts.pettripfinder.austin_tx_reader_refresh_002 --old-commit fcca4aad --work-dir C:/t/atx2n [--write]

READ ONLY over the market's own committed outputs. It re-runs nothing that captures: every quote it classifies is a
quote the source-ready order already captured and the refreshed clean authority already bound.

What it measures
----------------
1. THE OLD PACKAGE (pkg-austin-tx-3030caf7). FAST is re-run over it against the CURRENT live release with the
   builds declared not run: rule N (parent = current live) must fail, the lane must refuse eligibility, and no
   canonical receipt may select it. Its dependency digests are compared with the committed inputs they claim.
2. EVERY AUSTIN OPERATIVE QUOTE under the repaired reader, classified AFFIRMATIVE_ACCEPTANCE / EXPLICIT_REFUSAL /
   QUESTION_ONLY / AMBIGUOUS / SERVICE_ANIMAL_ONLY / NOT_OPERATIVE, against the row's disposition.
3. KALAHARI and THE FIVE REFUSAL-LANGUAGE HOLDS: quote, old disposition, new classification, new disposition.
4. THE FOUNDER COHORT, old and new, by class; the other safe holds (same-campus, Sentral, preopening, timeshare)
   unchanged.
5. THE STATIC LANE's own reader verdicts, re-read from its persisted artifacts under the repaired reader.
6. MARKET ACCOUNTING old / new, and THE READER-SAFETY PROOF over the NEW sealed package.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = Path(__file__).resolve().parents[2]
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

from scripts.pettripfinder import fast_release_lane as FL  # noqa: E402
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder import market_package_writer as W  # noqa: E402
from scripts.pettripfinder import registration_release_lane as LANE  # noqa: E402
from scripts.pettripfinder import release_index as RI  # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402

WORK_ORDER = "PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002"
MARKET_ID = "austin-tx"
PKG = _DASH / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
STAGING = PKG / "markets" / "staging" / MARKET_ID
LP = STAGING / "launch_package"
OLD_PACKAGE_ID = "pkg-austin-tx-3030caf7703a9c57"
OLD_PACKAGE = STAGING / "shadow_packages" / MARKET_ID / ("%s.json" % OLD_PACKAGE_ID)
OUT = REPORTS / "austin_tx_reader_refresh_002.json"

#: the five rows the source-ready order founder-held because the OLD shared reader could not read their refusal
OLD_REFUSAL_LANGUAGE_HOLDS = (
    "kalahari resorts and conventions round rock tx", "mountain star lodge and hotel",
    "at and t hotel and conference center", "strickland arms bed and breakfast", "heywood hotel")
TIMESHARE_NAMES = ("club wyndham austin", "worldmark austin", "raintree inn")

_FEE_NIGHTLY = re.compile(r"\b(?:per\s+night|nightly|a\s+night|/\s*night|per\s+day|daily|a\s+day|/\s*day)\b", re.I)


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _git_json(commit, rel):
    out = subprocess.run(["git", "-C", str(_DASH), "show", "%s:atlas-dashboard/%s" % (commit, rel)],
                         capture_output=True, check=True).stdout
    return json.loads(out.decode("utf-8-sig"))


def classify(quote, context=""):
    """One operative quote, read by the repaired reader exactly as FAST rule C reads it."""
    pf, pf_why = FPB.classify_quote(quote, kind=FPB.KIND_PET_FRIENDLY, context=context)
    np_, np_why = FPB.classify_quote(quote, kind=FPB.KIND_NO_PETS, context=context)
    reading = PR.parse(quote).pets_allowed
    if pf == FPB.ELIGIBLE:
        return "AFFIRMATIVE_ACCEPTANCE", pf_why
    if np_ == FPB.ELIGIBLE or reading is False:
        return "EXPLICIT_REFUSAL", np_why
    if FPB.CLASS_SERVICE_ANIMAL_ONLY in (pf, np_):
        return "SERVICE_ANIMAL_ONLY", pf_why
    if FPB.CLASS_QUOTE_CONTRADICTS in (pf, np_):
        return "AMBIGUOUS", pf_why if pf == FPB.CLASS_QUOTE_CONTRADICTS else np_why
    if "?" in quote:
        return "QUESTION_ONLY", pf_why
    return "NOT_OPERATIVE", pf_why


def old_package_invalidation(work_dir):
    old = _load(OLD_PACKAGE)
    live = RI.live_index()
    idx, state, problems = live
    if problems:
        raise SystemExit("current live could not be established: %s" % problems[:3])
    receipt = FL.run_fast_lane(old, work_dir=Path(work_dir), live=live, build=False, determinism=False,
                               participates=True)
    rules = OrderedDict((r, res["status"]) for r, res in receipt["RESULTS"].items())
    canonical = FL.eligible_receipts(MARKET_ID, old["package_digest"])
    historical = FL.eligible_receipts(MARKET_ID, old["package_digest"], STAGING / "shadow_receipts")
    current_inputs = W.inputs_from_committed_market(
        MARKET_ID, execution_zone=SMP.ZONE_SHADOW_UNTIL_REGISTERED,
        intended_delta=OrderedDict((("market_id", MARKET_ID),)), parent_live_state=LANE.parent_from_live(live),
        launch_package=LP, source_sha=old["created_from_source_sha"])
    stale = sorted(k for k, v in old["dependency_input_digests"].items()
                   if current_inputs.dependency_input_digests.get(k) != v)
    registerable = receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"] == FL.YES and bool(canonical) and not stale
    return OrderedDict((
        ("package_id", OLD_PACKAGE_ID), ("package_digest", old["package_digest"]),
        ("sealed_at", old.get("sealed_at")), ("created_from_source_sha", old.get("created_from_source_sha")),
        ("sealed_under", "the shared first-party reader BEFORE PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-"
                         "CORRECTION-001 (it read FAQ questions as acceptance and missed several refusal shapes)"),
        ("parent_live_deploy", old["parent_live_state"]["live_deploy_id"]),
        ("current_live_deploy", state.deploy_id),
        ("fast_today", OrderedDict((
            ("note", "re-run against the CURRENT live release with the two builds declared not run (J, K "
                     "UNKNOWN by design); a package that fails any rule today is not eligible"),
            ("rules", rules), ("failed", receipt["FAILED_RULES"]), ("unknown", receipt["UNKNOWN_RULES"]),
            ("rule_N_problems", (receipt["RESULTS"].get("N") or {}).get("problems")),
            ("ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"])))),
        ("canonical_receipts_selecting_it", [p.name for p in canonical]),
        ("historical_receipt_in_staging", [p.name for p in historical]),
        ("dependency_inputs_no_longer_committed", stale),
        ("OLD_PACKAGE_REGISTERABLE", "YES" if registerable else "NO"),
        ("OLD_PACKAGE_AUTHORIZABLE", "YES" if registerable else "NO"),
        ("kept_as_historical_evidence", True),
    ))


def interpretation(clean, old_clean):
    old_by = {r["identity_key"]: r for r in old_clean["rows"]}
    rows, table = [], Counter()
    for r in clean["rows"]:
        ev = r.get("evidence") or {}
        if not ev.get("quote"):
            continue
        cls, why = classify(ev["quote"], ev.get("context", ""))
        table[(r["disposition"], cls)] += 1
        rows.append(OrderedDict((("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
                                 ("disposition", r["disposition"]),
                                 ("old_disposition", (old_by.get(r["identity_key"]) or {}).get("disposition")),
                                 ("classification", cls), ("why", why[:200]), ("quote", ev["quote"][:400]))))
    pf = [x for x in rows if x["disposition"] == "CLEAN_PET_FRIENDLY"]
    return rows, OrderedDict((
        ("operative_quotes_classified", len(rows)),
        ("by_disposition_and_class", OrderedDict(("%s / %s" % k, v) for k, v in sorted(table.items()))),
        ("PET_FRIENDLY_NOT_AFFIRMATIVE", [x["identity_key"] for x in pf if x["classification"] != "AFFIRMATIVE_ACCEPTANCE"]),
        ("PET_FRIENDLY_WITH_EXPLICIT_REFUSAL", sum(1 for x in pf if x["classification"] == "EXPLICIT_REFUSAL")),
        ("QUESTION_ONLY_PET_FRIENDLY", sum(1 for x in pf if x["classification"] == "QUESTION_ONLY")),
        ("SERVICE_ANIMAL_ONLY_PET_FRIENDLY", sum(1 for x in pf if x["classification"] == "SERVICE_ANIMAL_ONLY")),
        ("QUESTION_ONLY_IS_NEVER_ACCEPTANCE", all(x["classification"] != "QUESTION_ONLY" for x in pf)),
    ))


def static_lane_reread():
    """The static lane recorded its OWN reader verdict per read; re-read each persisted block under the repaired
    reader. The lane is not re-run (63 of its targets have no cached attempt and would be refetched)."""
    from scripts.pettripfinder import austin_tx_free_static_capture_001 as S
    rep = _load(REPORTS / "austin_tx_free_static_capture_001.json")
    run = _DASH / "data" / "acquisition" / rep["run_id"]
    moved, reread = [], 0
    for r in rep["rows"]:
        text, old = None, None
        if r.get("observation") and r["brand"] != "MARRIOTT":
            old = (r["observation"].get("extraction") or {}).get("pets_allowed")
            p = _DASH / r["artifact_dir"] / "policy-block.txt" if r.get("artifact_dir") else None
            if p and p.is_file():
                text = p.read_text(encoding="utf-8", errors="replace")
        elif ((r.get("text_bound_read") or {}).get("reader") or {}).get("found") and r.get("artifact_dir"):
            old = r["text_bound_read"]["reader"].get("pets_allowed")
            dec = run / Path(r["artifact_dir"]).parent.name / "declined-01" / "rendered.html"
            if dec.is_file():
                html = dec.read_text(encoding="utf-8", errors="replace")
                hit = S.UC.locate_policy_in_html(html)
                if not hit.found:
                    hit = S.UC.locate_policy_in_text(S.ZCR.full_document_text(html))
                text = hit.text if hit.found else None
        if text is None:
            continue
        reread += 1
        new = PR.parse(text).pets_allowed
        if new != old:
            moved.append(OrderedDict((("identity_key", r["identity_key"]), ("outcome", r["outcome"]),
                                      ("old_reader", old), ("repaired_reader", new),
                                      ("block", " ".join(text.split())[:240]))))
    return OrderedDict((("reads_reread", reread), ("verdicts_moved", len(moved)), ("moved", moved),
                        ("why_not_rerun", "the lane would refetch the 63 targets with no cached attempt record; "
                                          "this order repeats no acquisition"),
                        ("effect", "none publishes: the clean authority's shared-reader gate re-reads every quote "
                                   "under the repaired reader before a row can publish")))


def accounting(clean):
    pf = sum(1 for r in clean["rows"] if r["disposition"] == "CLEAN_PET_FRIENDLY")
    np_ = sum(1 for r in clean["rows"] if r["disposition"] == "CLEAN_VERIFIED_NO_PETS")
    census = len(clean["rows"])
    return OrderedDict((("qualifying_census", census), ("pet_friendly", pf), ("verified_no_pets", np_),
                        ("resolved", pf + np_), ("unresolved", census - pf - np_),
                        ("resolution_rate_pct", round(100.0 * (pf + np_) / census, 2))))


def safety(package, census):
    pf = package["pet_friendly_records"]
    names = {(r.get("name") or "").lower() for r in pf}
    preopening = [r["identity_key"] for r in pf
                  if re.search(r"\b(?:opening|coming soon|opens)\b", r.get("name") or "", re.I)]
    timeshare_census = sorted(h["canonical_name"] for h in census.get("non_admitted") or ()
                              if "TIMESHARE" in str(h.get("classification_reason") or "").upper())
    timeshare_pf = sorted(n for n in names if any(t in n for t in TIMESHARE_NAMES))
    refusal, question, misleading = [], [], []
    for r in pf:
        for e in r.get("evidence") or ():
            if e.get("field") != "pets_allowed" or e.get("artifact_class") != "PUBLICATION_GRADE_EVIDENCE":
                continue
            cls, _why = classify(e["quote"])
            if cls == "EXPLICIT_REFUSAL":
                refusal.append(r["identity_key"])
            if cls == "QUESTION_ONLY":
                question.append(r["identity_key"])
        fee = (r.get("facts") or {}).get("pet_fee") or {}
        if fee:
            quote = " ".join(e.get("quote", "") for e in r.get("evidence") or () if e.get("field") == "pet_fee")
            # amounts are compared as numbers: "$50.00" and "$50" in one quote are ONE amount
            amounts = {float(a) for a in re.findall(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", quote)}
            basis = str(fee.get("basis") or fee.get("fee_basis") or "")
            if (basis == "per_stay" and _FEE_NIGHTLY.search(quote)) or len(amounts) > 1:
                misleading.append(r["identity_key"])
    gate = FPB.evaluate_package(package)
    return OrderedDict((
        ("PET_FRIENDLY_WITH_EXPLICIT_REFUSAL", len(refusal)), ("refusal_rows", refusal),
        ("QUESTION_ONLY_PET_FRIENDLY", len(question)), ("question_only_rows", question),
        ("PREOPENING_PROFILES_PUBLISHED", len(preopening)),
        ("timeshare_identities_excluded_by_census", timeshare_census),
        ("VACATION_OWNERSHIP_TIMESHARE_PROFILES_PUBLISHED", len(timeshare_pf)),
        ("MISLEADING_SINGLE_FEES", len(misleading)), ("misleading_rows", misleading),
        ("rule_C_over_new_package", OrderedDict((k, gate[k]) for k in ("records_evaluated", "eligible",
                                                                         "ineligible", "passed"))),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-commit", default="fcca4aad", help="the source-ready order's final commit")
    ap.add_argument("--work-dir", required=True, help="a SHORT ABSOLUTE forward-slash scratch dir (C:/t/x)")
    ap.add_argument("--new-package", required=True, help="the refreshed shadow package (path)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    if "\t" in args.work_dir or not args.work_dir.startswith("C:/"):
        raise SystemExit("--work-dir must be a short absolute forward-slash path")
    rel_clean = "launch_packages/pettripfinder/markets/reports/austin_tx_clean_authority_001.json"
    rel_act = "launch_packages/pettripfinder/markets/reports/austin_tx_actionability_001.json"
    clean, old_clean = _load(_DASH / rel_clean), _git_json(args.old_commit, rel_clean)
    act, old_act = _load(_DASH / rel_act), _git_json(args.old_commit, rel_act)
    new_package = _load(args.new_package)
    census = _load(LP / "identity_census" / ("%s.json" % MARKET_ID))
    rows, interp = interpretation(clean, old_clean)
    by_key = {r["identity_key"]: r for r in clean["rows"]}
    old_by_key = {r["identity_key"]: r for r in old_clean["rows"]}
    holds = []
    for key in OLD_REFUSAL_LANGUAGE_HOLDS:
        new_row, old_row = by_key[key], old_by_key[key]
        ev = new_row.get("evidence") or {}
        cls, why = classify(ev.get("quote", ""), ev.get("context", ""))
        holds.append(OrderedDict((("property", new_row["canonical_name"]), ("identity_key", key),
                                  ("quote", ev.get("quote")), ("old_disposition", old_row["disposition"]),
                                  ("old_hold_reason", (old_row.get("hold_reason") or "")[:300]),
                                  ("new_classification", cls), ("why", why[:240]),
                                  ("new_disposition", new_row["disposition"]),
                                  ("new_hold_reason", (new_row.get("hold_reason") or "")[:300]))))
    resolved = [h for h in holds if h["new_disposition"] == "CLEAN_VERIFIED_NO_PETS"]
    exclusions = _load(LP / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")["exclusions"]
    kal = next(h for h in holds if h["identity_key"].startswith("kalahari"))
    kal_excl = [e for e in exclusions if e["normalized_name"] == kal["identity_key"]]
    old_founder = [r for r in old_act["rows"] if r["actionability"] == "REQUIRES_FOUNDER"]
    new_founder = [r for r in act["rows"] if r["actionability"] == "REQUIRES_FOUNDER"]

    def founder_classes(frows):
        c = Counter()
        for r in frows:
            if r["disposition"] == "IDENTITY_MISMATCH_HOLD":
                c["dual_brand_rows"] += 1
            elif "two first-party routes" in (r.get("reason") or r.get("why") or ""):
                c["operator_domain_route_rulings"] += 1
            else:
                c["refusal_language_rows"] += 1
        return OrderedDict(sorted(c.items()))

    same_campus = sorted(h["canonical_name"] for h in census.get("non_admitted") or ()
                         if h.get("classification") == "SAME_CAMPUS_DISTINCT_ENTITY")
    sentral = [h["classification"] for h in census.get("non_admitted") or ()
               if "sentral" in (h.get("canonical_name") or "").lower()]
    doc = OrderedDict((
        ("schema", "ptf-market-reader-refresh/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("old_source_ready_commit", args.old_commit),
        ("old_package", old_package_invalidation(args.work_dir)),
        ("interpretation", interp),
        ("kalahari", OrderedDict((("quote", kal["quote"]), ("old_disposition", kal["old_disposition"]),
                                  ("new_classification", kal["new_classification"]),
                                  ("new_disposition", kal["new_disposition"]),
                                  ("KALAHARI_PET_FRIENDLY", "NO" if kal["new_disposition"] != "CLEAN_PET_FRIENDLY"
                                   else "YES"),
                                  ("canonical_verified_no_pets_exclusion",
                                   OrderedDict((k, kal_excl[0][k]) for k in ("exclusion_id", "exclusion_state",
                                                                             "evidence_quote", "source_url",
                                                                             "record_hash", "approval_hash"))
                                   if kal_excl else None)))),
        ("old_refusal_language_holds", holds),
        ("OLD_REFUSAL_LANGUAGE_HOLDS", len(holds)), ("REFUSAL_LANGUAGE_ROWS_RESOLVED", len(resolved)),
        ("REMAINING_REFUSAL_LANGUAGE_HOLDS", len(holds) - len(resolved)),
        ("founder_cohort", OrderedDict((
            ("OLD_FOUNDER_ROWS", len(old_founder)), ("old_by_class", founder_classes(old_founder)),
            ("ROWS_RESOLVED_BY_REPAIRED_READER", len({r["identity_key"] for r in old_founder}
                                                     - {r["identity_key"] for r in new_founder})),
            ("NEW_FOUNDER_ROWS", len(new_founder)), ("new_by_class", founder_classes(new_founder)),
            ("identity_resolutions_written", False)))),
        ("other_safe_holds_preserved", OrderedDict((
            ("same_campus_distinct_entity_rows", same_campus), ("same_campus_count", len(same_campus)),
            ("sentral_east_austin", sentral),
            ("preopening_held", clean.get("preopening_held")),
            ("timeshare_excluded", sorted(h["canonical_name"] for h in census.get("non_admitted") or ()
                                          if "TIMESHARE" in str(h.get("classification_reason") or "").upper()))))),
        ("static_lane_reread", static_lane_reread()),
        ("accounting", OrderedDict((("old", accounting(old_clean)), ("new", accounting(clean)),
                                    ("actionable_unresolved_old", old_act["actionable_unresolved_remaining"]),
                                    ("actionable_unresolved_new", act["actionable_unresolved_remaining"]),
                                    ("totals_by_class_new", act["totals_by_class"]),
                                    ("by_disposition_new", act["by_disposition"]),
                                    ("TECHNICAL_SOURCE_READY", act["TECHNICAL_SOURCE_READY"]),
                                    ("COVERAGE_READY", act["COVERAGE_READY"])))),
        ("reader_safety_new_package", safety(new_package, census)),
        ("rows", rows),
    ))
    print(json.dumps(OrderedDict((k, doc[k]) for k in (
        "old_package", "interpretation", "OLD_REFUSAL_LANGUAGE_HOLDS", "REFUSAL_LANGUAGE_ROWS_RESOLVED",
        "REMAINING_REFUSAL_LANGUAGE_HOLDS", "founder_cohort", "accounting", "reader_safety_new_package")),
        indent=1, ensure_ascii=False)[:9000])
    for h in holds:
        print("HOLD", h["property"], "|", h["old_disposition"], "->", h["new_classification"], "/", h["new_disposition"])
    print("static lane:", doc["static_lane_reread"]["reads_reread"], "reread,", doc["static_lane_reread"]["verdicts_moved"],
          "moved")
    if args.write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("written", OUT.relative_to(_DASH).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
