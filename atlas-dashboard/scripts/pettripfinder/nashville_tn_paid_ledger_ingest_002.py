"""PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 -- the paid-attempt ingestion.

Records the Firecrawl run PTF-NASHVILLE-TN-NEW-MARKET-001 actually made into
the shared paid-attempt ledger. It makes NO new paid request: it reads the
committed run report and writes what that report already states.

WHY THIS IS DERIVATION AND NOT INVENTION

Rule O of the fast release lane requires a published fact read through a paid
lane to name the reservation that bought it: the provider, the run, an attempt
id that re-derives, and the hash of the REQUEST ENVELOPE. Lexington could not
supply the last one -- its committed Firecrawl report carried no envelope at
all -- so PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 held six rows
rather than fabricate a hash, which was right.

Nashville's committed report is different in exactly the way that matters.
``nashville_tn_firecrawl_pass_001.json`` carries, for all seventeen attempted
rows, the ``request_envelope`` the adapter sent -- the endpoint and the exact
body -- plus the page hash, the outcome, the identity assessment, the capture
timestamp and the credit delta that was the meter. Every field the ledger
contract wants is present in committed bytes, so the ledger row is DERIVED. No
value here is chosen by this module.

WHAT IS RE-KEYED, AND WHY

The run recorded each row under the SHORT identity key the lane captured it
under; the registered census keys the same property under its fuller canonical
name and carries the short form as an alias. Rule O re-derives the attempt id
from the identity key the EVIDENCE REFERENCE carries, which is the registered
one, so the ledger row is written under the registered key and the capture key
is preserved alongside it in ``property_identity``. Re-keying through the
census's own alias table is a join, not a decision.

WHAT IT WILL NOT DO

It will not ingest a row the report did not attempt, will not invent an
envelope for a row that carries none, and will not write a credit figure the
report does not state. ``--check`` reports and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder import sealed_market_package as SMP            # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"
SHADOW_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
LANE = "firecrawl"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORT = os.path.join(PKG, "markets", "reports", "nashville_tn_firecrawl_pass_001.json")
CENSUS = os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID)
PROPOSED_CENSUS = os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID)
LEDGER = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")


class IngestError(RuntimeError):
    """Refuse to write a ledger row the committed run does not state."""


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def registered_key_map():
    """``captured key -> registered key``, from the census's own alias table."""
    path = CENSUS if os.path.isfile(CENSUS) else PROPOSED_CENSUS
    doc = _load(path)
    out = {}
    for row in doc["hotels"]:
        out[row["identity_key"]] = row["identity_key"]
        for alias in row.get("identity_key_aliases") or ():
            out.setdefault(alias, row["identity_key"])
    return out, path


def build_records():
    report = _load(REPORT)
    if str(report.get("market_id")) != MARKET_ID:
        raise IngestError("this report is not Nashville's")
    run_id = str(report.get("run_id") or "")
    if not run_id:
        raise IngestError("the report states no run id")
    credits = report.get("credits") or {}
    attempted = int(report.get("attempted_rows") or 0)
    delta = credits.get("delta")
    if delta is None:
        raise IngestError("the report states no credit delta, and none may be inferred")
    per_attempt = float(delta) / attempted if attempted else 0.0

    keys, census_path = registered_key_map()
    rows = list(report.get("rows") or ())
    if len(rows) != attempted:
        raise IngestError("the report states %d attempted rows and carries %d"
                          % (attempted, len(rows)))

    records = []
    for row in rows:
        captured = str(row.get("identity_key") or "")
        if not captured:
            raise IngestError("a run row carries no identity key")
        key = keys.get(captured, captured)
        envelope = row.get("request_envelope")
        if not isinstance(envelope, dict):
            raise IngestError("%s: the run row carries no request envelope, so no reservation "
                              "can be derived for it" % captured)
        record = PAL.build_attempt(
            {"identity_key": key,
             "canonical_name": row.get("canonical_name"),
             "brand": row.get("family"),
             "property_code": row.get("property_code"),
             "canonical_url": row.get("final_url") or row.get("requested_url"),
             "url": row.get("final_url") or row.get("requested_url"),
             "street": row.get("expected_street"),
             "postal_code": row.get("expected_postal_code"),
             "outcome": row.get("outcome"),
             "final_state": ("ACQUIRED_PUBLICATION_GRADE"
                             if row.get("outcome") == "VALID" and row.get("identity_confirmed")
                             else ""),
             "publication_grade": bool(row.get("outcome") == "VALID"
                                       and row.get("identity_confirmed")),
             "attempted_at": row.get("captured_at"),
             "reader": str(((row.get("identity_assessment") or {}).get("binding_method")) or ""),
             "content_hash": row.get("page_sha256"),
             "artifact_dir": row.get("artifact_dir"),
             "provider": LANE,
             "providers_tried": [LANE]},
            market_id=MARKET_ID, work_order=SHADOW_ORDER, run_id=run_id, lane=LANE,
            cost_usd_minor=0.0, firecrawl_credits=per_attempt)
        # The provenance rule O checks, alongside the ledger row it lives with.
        record["request_envelope_sha256"] = SMP.sha256_text(SMP.canonical_json(envelope))
        record["captured_identity_key"] = captured
        record["ingested_by"] = WORK_ORDER
        records.append(record)
    return run_id, records, census_path, report


def reservations_from_ledger(market_id=MARKET_ID, path=LEDGER):
    """``artifact digest -> reservation`` for one market, from the committed ledger.

    The shared paid-attempt ledger IS the provenance authority once a run is
    ingested, so the reservation a release package carries is read back out of
    it rather than re-derived from the run report a second time. A ledger row
    with no artifact hash or no envelope hash yields nothing: rule O then
    refuses the reference, which is correct.
    """
    if not os.path.isfile(path):
        return {}
    out = {}
    for attempt in (_load(path).get("attempts") or ()):
        if attempt.get("market_id") != market_id:
            continue
        digest = str(attempt.get("artifact_hash") or "").strip()
        envelope = str(attempt.get("request_envelope_sha256") or "").strip()
        if not digest or not envelope:
            continue
        if not digest.startswith("sha256:"):
            digest = "sha256:" + digest
        out[digest] = OrderedDict([
            ("provider", "Firecrawl"),
            ("lane", str(attempt.get("lane") or LANE)),
            ("run_id", str(attempt.get("run_id") or "")),
            ("attempt_id", str(attempt.get("attempt_id") or "")),
            ("request_envelope_sha256", envelope),
        ])
    return out


def ledger_lookup(path=LEDGER):
    """A rule-O cross-check: is this reservation actually in the ledger?"""
    known = set()
    if os.path.isfile(path):
        known = {str(a.get("attempt_id") or "") for a in (_load(path).get("attempts") or ())}

    def _lookup(reservation):
        return str((reservation or {}).get("attempt_id") or "") in known

    return _lookup


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="derive and report, write nothing")
    args = ap.parse_args(argv)

    run_id, records, census_path, report = build_records()
    ledger = PAL.load(LEDGER)
    before = len(ledger.get("attempts") or ())
    existing = {str(a.get("attempt_id")) for a in (ledger.get("attempts") or ())}
    new = [r for r in records if r["attempt_id"] not in existing]

    print("run             :", run_id)
    print("census join     :", os.path.relpath(census_path, _DASH))
    print("credits         : before %s, after %s, delta %s"
          % (report["credits"].get("before"), report["credits"].get("after"),
             report["credits"].get("delta")))
    print("derived rows    : %d (%d already in the ledger)"
          % (len(records), len(records) - len(new)))
    print("outcomes        :", dict(Counter(r["outcome"] for r in records)))
    print("publication     : %d of %d" % (sum(1 for r in records if r["publication_grade"]),
                                          len(records)))
    print("envelope hashes : %d of %d derived"
          % (sum(1 for r in records if r.get("request_envelope_sha256")), len(records)))
    if args.check:
        print("ledger          : %d attempts, unchanged (--check)" % before)
        return 0

    merged = PAL.merge(ledger, records)
    PAL.save(LEDGER, merged)
    print("ledger          : %d -> %d attempts" % (before, len(merged["attempts"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
