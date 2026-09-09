"""PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 -- the authorized Firecrawl pass.

The order authorizes UP TO 10 plan credits for ONE exact cohort: the rows
`acquisition.ladder.firecrawl_candidacy` marked FIRECRAWL_ROUTED_FOR_FAMILY in
the committed `lexington_ky_paid_readiness_001.json`. The cohort is re-derived
here mechanically and the run REFUSES to start if it is not identical, or if it
exceeds 10 rows.

Cost discipline, from standing doctrine:

  * Firecrawl cost is BIMODAL -- 1 credit on a success, 0 when the origin
    refuses every engine. The 0.54 blended average is NOT a ceiling. The cap is
    therefore on ATTEMPTS, hard-stopped at 10, and never on an estimated spend.
  * The account balance is NOT a cost meter: it settles late. The balance is
    read before and after for the record, but the run stops on the ATTEMPT
    counter, not on the balance.
  * Pay once per page ever. Every URL is checked against the per-call ledger
    before the call, and a URL already bought is skipped, not re-bought.

Every call records requested URL, final URL, provider request id, content
sha256, credits reported and the deterministic request envelope. Nothing here
writes authority, a shared global, a pin, or a committed ledger: the per-call
ledger lives under the gitignored `data/`.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402
from scripts.pettripfinder.acquisition import ladder as L  # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402

WORK_ORDER = "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
PAID = os.path.join(REPORTS, "lexington_ky_paid_readiness_001.json")

AUTHORIZED_MAX_ROWS = 10
AUTHORIZED_MAX_CREDITS = 10
SPACING_SECONDS = 2.0


def rj(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def bought_urls():
    """Every URL this repository has already spent a Firecrawl credit on."""
    p = FC.CALL_LEDGER_PATH
    out = set()
    lines = 0
    if not Path(p).exists():
        return out, lines
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        lines += 1
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        for k in ("requested_url", "url", "final_url"):
            v = rec.get(k) or (rec.get("provenance") or {}).get(k)
            if v:
                out.add(v)
    return out, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--run-id", default="lexington_ky_firecrawl_002")
    ap.add_argument("--max-attempts", type=int, default=AUTHORIZED_MAX_ROWS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    routing = {r["identity_key"]: r for r in rj(ROUTING)["identities"]}
    committed = rj(PAID)
    committed_cohort = [r for r in committed["rows"] if r["firecrawl_candidate"]]

    # --- re-derive the cohort mechanically; refuse if it moved -------------
    already, ledger_lines = bought_urls()
    rederived = []
    for r in rj(ROUTING)["identities"]:
        url = r.get("route") or ""
        if not url:
            continue
        c = L.firecrawl_candidacy(
            family=r["brand"], url=url,
            prior_static_outcome=(r.get("static") or {}).get("outcome") or "",
            firecrawl_already_tried=url in already)
        if c.candidate:
            rederived.append(r)

    committed_keys = sorted((r["identity_key"], r["url"]) for r in committed_cohort)
    rederived_keys = sorted((r["identity_key"], r["route"]) for r in rederived)
    identical = committed_keys == rederived_keys

    gate = OrderedDict([
        ("authorized_max_rows", AUTHORIZED_MAX_ROWS),
        ("authorized_max_credits", AUTHORIZED_MAX_CREDITS),
        ("committed_cohort_rows", len(committed_cohort)),
        ("rederived_cohort_rows", len(rederived)),
        ("cohort_identical_to_committed_plan", identical),
        ("within_authorization", identical and len(rederived) <= AUTHORIZED_MAX_ROWS),
    ])
    if not gate["within_authorization"]:
        gate["decision"] = ("REFUSED -- the cohort is not the one the order authorized. "
                            "No call was made.")
        print(json.dumps(gate, indent=1))
        out = args.out or os.path.join(REPORTS, "lexington_ky_firecrawl_pass_002.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(OrderedDict([("schema", "ptf-firecrawl-pass/1.0"),
                                   ("work_order", WORK_ORDER), ("gate", gate),
                                   ("calls", 0), ("credits_used", 0)]), fh, indent=1)
            fh.write("\n")
        return 2
    gate["decision"] = "PROCEED -- cohort matches the committed plan and is within cap"

    balance_before = FC.credits_remaining()
    print("cohort", len(rederived), "| credits before:", balance_before, flush=True)
    if args.dry_run:
        gate["decision"] = "DRY RUN -- no call made"
        print(json.dumps(gate, indent=1))
        return 0

    run_dir = Path(_DASH) / "data" / "acquisition" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    attempts = 0
    for r in rederived:
        if attempts >= args.max_attempts:
            rows.append(OrderedDict([
                ("identity_key", r["identity_key"]), ("name", r["name"]),
                ("outcome", "NOT_ATTEMPTED_ATTEMPT_CAP_REACHED"),
                ("why", "the hard attempt cap of %d authorized calls was reached"
                 % args.max_attempts)]))
            continue
        url = r["route"]
        if url in already:
            rows.append(OrderedDict([
                ("identity_key", r["identity_key"]), ("name", r["name"]),
                ("outcome", "SKIPPED_ALREADY_BOUGHT"),
                ("why", "this exact URL is already in the per-call ledger; pay once per "
                        "page ever")]))
            continue

        slug = r["slug"]
        target = BC.CaptureTarget(
            slug=slug, hotel=r["name"], requested_url=url,
            property_code=r.get("route_property_code", "") or "",
            market_id=MARKET_ID, normalized_name=r["identity_key"],
            identity_key=r["identity_key"],
            street_identity=r.get("address_line", ""),
            expected_postal_code=(r.get("postal_code") or "")[:5],
            expected_street=r.get("address_line", ""),
            expected_phone="",
            expected_locality=r.get("city", "") or "Lexington",
            identity_brand=r["brand"], census_matched=True)

        time.sleep(SPACING_SECONDS)
        attempts += 1
        attempt_dir = run_dir / slug / "attempt-01"
        try:
            rec, _payload = FC.run_attempt(target, 1, run_dir=run_dir, brand=r["brand"])
            a = as_plain(rec)
        except Exception as exc:  # noqa: BLE001
            rows.append(OrderedDict([
                ("identity_key", r["identity_key"]), ("name", r["name"]),
                ("requested_url", url), ("outcome", "FIRECRAWL_FAILED"),
                ("error", FC.redact(repr(exc))[:300])]))
            continue

        row = OrderedDict([
            ("identity_key", r["identity_key"]), ("name", r["name"]),
            ("brand", r["brand"]), ("requested_url", url),
            ("outcome", a.get("outcome")), ("final_url", a.get("final_url")),
            ("title", (a.get("title") or "")[:140]),
            ("detail", (a.get("detail") or "")[:300]),
            ("identity_assessment", a.get("identity")),
            ("artifact_dir", str(attempt_dir.relative_to(Path(_DASH))).replace("\\", "/")
             if attempt_dir.is_dir() else ""),
        ])

        if a.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": r["identity_key"], "canonical_name": r["name"],
                "brand": r["brand"], "corridor": r.get("cell_id", ""),
                "source_url": url, "outcome": "VALID",
                "final_url": a.get("final_url") or url,
                "artifact_dir": str(attempt_dir),
                "identity_confirmed": bool((a.get("identity") or {}).get("confirmed", True)),
                "locator_strategy": "",
            }
            try:
                obs, grade, refusal = MOS.observation_for(
                    result, run_id=args.run_id, market_id=MARKET_ID, census_row=None)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade), ("refusal_reason", refusal),
                ])
                pa = ext.get("pets_allowed")
                pg_ok = bool(grade) and str(
                    (grade or {}).get("verdict") or (grade or {}).get("grade") or ""
                ).endswith("CONFIRMED")
                if pa is True:
                    row["firecrawl_class"] = ("FIRECRAWL_PUBLICATION_GRADE" if pg_ok
                                              else "FIRECRAWL_IDENTITY_ONLY")
                    row["policy_class"] = ("CLEAN_PET_FRIENDLY" if pg_ok
                                           else "POLICY_NOT_FOUND")
                elif pa is False:
                    row["firecrawl_class"] = ("FIRECRAWL_PUBLICATION_GRADE" if pg_ok
                                              else "FIRECRAWL_IDENTITY_ONLY")
                    row["policy_class"] = ("CLEAN_VERIFIED_NO_PETS" if pg_ok
                                           else "POLICY_NOT_FOUND")
                else:
                    row["firecrawl_class"] = "FIRECRAWL_SOURCE_SILENT"
                    row["policy_class"] = "SOURCE_SILENT"
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = FC.redact(repr(exc))[:300]
                row["firecrawl_class"] = "FIRECRAWL_FAILED"
                row["policy_class"] = "CAPTURE_FAILED"
        elif a.get("outcome") == "VALID":
            row["firecrawl_class"] = "FIRECRAWL_SOURCE_SILENT"
            row["policy_class"] = "POLICY_NOT_FOUND"
        elif a.get("outcome") == "IDENTITY_MISMATCH":
            row["firecrawl_class"] = "FIRECRAWL_MISMATCH"
            row["policy_class"] = "IDENTITY_MISMATCH"
        elif a.get("outcome") in ("ACCESS_DENIED", "BLANK_PAGE", "UNHYDRATED"):
            row["firecrawl_class"] = "FIRECRAWL_BLOCKED"
            row["policy_class"] = "CAPTURE_FAILED"
        else:
            row["firecrawl_class"] = "FIRECRAWL_FAILED"
            row["policy_class"] = "CAPTURE_FAILED"

        rows.append(row)
        print(f"  [{attempts}/{args.max_attempts}] {r['name'][:34]:35s} "
              f"{row.get('firecrawl_class','')}", flush=True)

    balance_after = FC.credits_remaining()
    _, ledger_after = bought_urls()

    classes = Counter(r.get("firecrawl_class", r.get("outcome", "")) for r in rows)
    policy = Counter(r.get("policy_class", "NOT_ATTEMPTED") for r in rows)

    report = OrderedDict([
        ("schema", "ptf-firecrawl-pass/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("run_id", args.run_id),
        ("gate", gate),
        ("cost_doctrine",
         "Firecrawl cost is BIMODAL -- 1 credit on a success, 0 when the origin refuses every "
         "engine. The cap is on ATTEMPTS (hard-stopped at %d), never on an estimated spend. "
         "The account balance is not a cost meter: it settles late, so it is recorded for the "
         "audit trail and is not what stopped the run." % args.max_attempts),
        ("attempts_made", attempts),
        ("attempt_cap", args.max_attempts),
        ("credits_balance_before", balance_before),
        ("credits_balance_after", balance_after),
        ("credits_delta", (balance_before - balance_after)
         if (balance_before is not None and balance_after is not None) else None),
        ("per_call_ledger", OrderedDict([
            ("path", "data/acquisition/firecrawl_call_ledger.jsonl (gitignored)"),
            ("lines_before", ledger_lines), ("lines_after", ledger_after),
        ])),
        ("double_buy_check", OrderedDict([
            ("urls_already_bought_before_run", len(already)),
            ("rows_skipped_as_already_bought",
             len([r for r in rows if r.get("outcome") == "SKIPPED_ALREADY_BOUGHT"])),
        ])),
        ("bright_data_calls", 0),
        ("places_calls", 0),
        ("usd_spent", 0.0),
        ("totals", OrderedDict([
            ("rows", len(rows)),
            ("firecrawl_classes", OrderedDict(sorted(classes.items()))),
            ("policy_classes", OrderedDict(sorted(policy.items()))),
        ])),
        ("rows", rows),
    ])
    out = args.out or os.path.join(REPORTS, "lexington_ky_firecrawl_pass_002.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=str)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("credits before/after:", balance_before, balance_after)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
