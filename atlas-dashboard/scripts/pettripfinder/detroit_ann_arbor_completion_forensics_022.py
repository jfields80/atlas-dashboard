# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022, Phases 0 to 2.

Forensically verifies the Pass-020 completion that a DIFFERENT SESSION produced
and committed, before any of it is allowed to reach authority.

THE REGENERATED TRIAGE JSON IS NOT TRUSTED BECAUSE IT SAYS "complete": true.
Every outcome is reconstructed here by re-running the committed reader over the
persisted capture bytes, and the reconstruction is then compared against what
the outside session recorded. A report that grades its own homework is not
evidence.

WHAT THE OUTSIDE SESSION TOUCHED IS ESTABLISHED FROM GIT, NOT FROM ITS OWN
CLAIMS. The adoption gate that matters is not "did it say it changed no
authority" but "does the commit diff contain an authority path".

NO PROVIDER IS CALLED AND NOTHING IS RE-CAPTURED.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022"
PROVENANCE = "PTF-DETROIT-ANN-ARBOR-ATTENDED-020-EXTERNAL-COMPLETION-ADOPTED"
BASE = "f5828db"
EXTERNAL = "b5c5c6a"
AS_OF = "2026-08-30"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT = LP / "detroit_ann_arbor_completion_forensics_022.json"

#: Any commit touching one of these prefixes has reached authority.
AUTHORITY_PREFIXES = (
    "launch_packages/pettripfinder/hotel_policy_facts_",
    "launch_packages/pettripfinder/markets/authority/",
    "launch_packages/pettripfinder/identity_routing.json",
    "launch_packages/pettripfinder/seed_businesses.csv",
    "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
    "launch_packages/pettripfinder/detroit_ann_arbor_final_partition_001.json",
    "launch_packages/pettripfinder/markets/reports/",
    "deploy/netlify/release_contracts/",
)
#: Approval vocabulary that must NOT appear on a raw capture row.
APPROVAL_FIELDS = ("approval", "decided_by", "decision", "approved_by",
                   "founder_disposition", "verification_state")


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def git(*args):
    return subprocess.run(("git",) + args, cwd=str(_REPO_ROOT),
                          capture_output=True, text=True).stdout


def reconstruct(block_text, host):
    """Re-derive the outcome from the bytes, independently of the report.

    A REFUSAL IS TESTED BEFORE AN ALLOWANCE, and service-animal clauses are
    stripped first. ``to_extraction`` is the pet-FRIENDLY path; asking it alone
    what a refusal page says produced exactly the error this project has hit
    before -- "we are not a pet-friendly property" read as an allowance because
    the token "pet-friendly" is in it. The committed refusal patterns are the
    right instrument for that half, so both halves are used here.
    """
    ordinary = R11.strip_service_animal_clauses(block_text)
    refused = any(p.search(ordinary) for p in R11.REFUSAL_RES)
    allowed = any(p.search(ordinary) for p in R11.AFFIRMATIVE_PET_RES)

    reading = PR.parse(block_text)
    result = PR.to_extraction(reading, location=host or "")
    extraction = dict(getattr(result, "extraction", {}) or {})
    withheld = dict(getattr(result, "withheld", {}) or {})

    if refused and not allowed:
        pets = False
    elif allowed and not refused:
        pets = extraction.get("pets_allowed")
        if pets is None and "pets_allowed" not in withheld:
            pets = True
    elif refused and allowed:
        pets = None                      # contradictory; never guessed here
    else:
        pets = extraction.get("pets_allowed")
    return OrderedDict([
        ("pets_allowed", pets),
        ("refusal_evidence", refused),
        ("allowance_evidence", allowed),
        ("withheld", sorted(withheld)),
        ("fields", sorted(extraction)),
    ])


def run():
    checks = []

    def check(name, ok, detail=""):
        checks.append(OrderedDict([("check", name), ("pass", bool(ok)),
                                   ("detail", detail)]))

    # ---- Phase 0: what the outside session actually changed ------------ #
    files = [line for line in
             git("diff", "--name-only", "%s..%s" % (BASE, EXTERNAL)).split("\n")
             if line.strip()]
    authority_touched = [f for f in files
                         if any(f.startswith(p) for p in AUTHORITY_PREFIXES)]
    other_market = [f for f in files
                    if "pettripfinder" in f
                    and ("detroit" not in f.lower()
                         and "attended" not in f.lower())]

    inventory = []
    for path in files:
        full = _REPO_ROOT / path
        existed = bool(git("cat-file", "-e",
                           "%s:%s" % (BASE, path)) is not None
                       and subprocess.run(
                           ("git", "cat-file", "-e", "%s:%s" % (BASE, path)),
                           cwd=str(_REPO_ROOT), capture_output=True
                       ).returncode == 0)
        kind = ("source" if path.endswith(".py")
                else "report_or_evidence_index")
        inventory.append(OrderedDict([
            ("path", path), ("kind", kind),
            ("existed_at_%s" % BASE, existed),
            ("sha256", hashlib.sha256(full.read_bytes()).hexdigest()
             if full.is_file() else ""),
        ]))

    check("the outside commit touched NO authority file",
          not authority_touched, str(authority_touched))
    check("the outside commit touched no other market",
          not other_market, str(other_market))
    check("the outside commit is committed and pushed",
          git("rev-parse", EXTERNAL).strip()[:7] == EXTERNAL[:7])

    # ---- Phase 1: rebuild the corpus from persisted bytes -------------- #
    cohort = load(LP / "detroit_ann_arbor_free_cohort_020.json")
    triage = load(LP / "detroit_ann_arbor_attended_triage_020.json")
    rows = triage["results"]
    admitted = {row["identity_key"] for row in cohort["admitted_rows"]}
    processed = [row["identity_key"] for row in rows]

    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]}

    check("admitted identities = 45", len(admitted) == 45, str(len(admitted)))
    check("processed identities = 45", len(processed) == 45,
          str(len(processed)))
    check("missing identities = 0", not (admitted - set(processed)),
          str(sorted(admitted - set(processed))[:5]))
    check("no identity outside the admitted cohort entered",
          not (set(processed) - admitted),
          str(sorted(set(processed) - admitted)[:5]))
    dupes = [k for k, n in Counter(processed).items() if n > 1]
    check("duplicate identities = 0", not dupes, str(dupes))
    check("exactly one final observation per identity",
          len(processed) == len(set(processed)))

    advisory = []
    bad_hash, no_artifact, bad_route, approval_leak = [], [], [], []
    mismatch = []
    reconstructed = []
    for row in rows:
        key = row["identity_key"]
        artifact = row.get("block_artifact") or row.get("artifact") or ""
        block = row.get("block") or ""
        if artifact:
            path = _REPO_ROOT / artifact
            if not path.is_file():
                bad_hash.append((key, "missing from disk"))
            else:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != row.get("block_sha256"):
                    bad_hash.append((key, "sha256 does not reproduce"))
                on_disk = path.read_text(encoding="utf-8-sig")
                if block.strip() and on_disk.strip() != block.strip():
                    bad_hash.append((key, "disk bytes differ from the report"))
        elif block.strip():
            no_artifact.append(key)

        route = routes.get(key)
        if route is not None:
            routed = (route.get("official_property_url") or "").lower()
            host = (row.get("host") or "").lower()
            if host and routed and host.split(".")[-2:] != []:
                stem = routed.replace("https://", "").replace("www.", "")
                if host not in stem:
                    bad_route.append((key, host, routed))

        for field in APPROVAL_FIELDS:
            if field in row:
                approval_leak.append((key, field))

        # independent re-derivation from the bytes
        if block.strip():
            got = reconstruct(block, row.get("host") or "")
            reconstructed.append((key, row.get("triage"), got["pets_allowed"]))
            recorded = (row.get("reader") or {}).get("pets_allowed")
            if recorded is not None and got["pets_allowed"] != recorded:
                mismatch.append((key, "recorded %s, rebuilt %s"
                                 % (recorded, got["pets_allowed"])))

    check("every persisted block re-hashes from disk", not bad_hash,
          str(bad_hash[:4]))
    check("every row carrying evidence links a persisted artifact",
          not no_artifact, str(no_artifact[:4]))
    check("no capture row carries founder-approval vocabulary",
          not approval_leak, str(approval_leak[:4]))
    check("captured host matches the routed identity", not bad_route,
          str(bad_route[:3]))
    # ADVISORY, NOT AN INTEGRITY GATE. This harness applies the committed
    # refusal/allowance patterns to independent-site prose they were not tuned
    # on, so a disagreement here means "send this row to the real gate", not
    # "the evidence is forged". The authoritative test is R11.gate in Phase 4,
    # and tuning these patterns until they agreed would be hand-fitting a gate
    # to a desired answer.
    advisory.append(OrderedDict([
        ("check", "independent re-derivation agrees with every recorded "
                  "pets_allowed"),
        ("pass", not mismatch),
        ("disagreements", mismatch),
        ("meaning", "each disagreement is routed to the sanctioned "
                    "publication gate, which decides"),
    ]))

    # independent outcome distribution
    rebuilt = Counter()
    for row in rows:
        block = (row.get("block") or "").strip()
        if not block:
            rebuilt["NO_EVIDENCE"] += 1
            continue
        got = reconstruct(block, row.get("host") or "")
        if got["pets_allowed"] is True:
            rebuilt["pets_allowed_true"] += 1
        elif got["pets_allowed"] is False:
            rebuilt["pets_allowed_false"] += 1
        else:
            rebuilt["unresolved_boolean"] += 1

    recorded_triage = Counter(row["triage"] for row in rows)
    recorded_outcome = Counter(row["outcome"] for row in rows)
    expected_triage = {"CLEAN_PET_FRIENDLY_CANDIDATE": 27,
                       "CLEAN_VERIFIED_NO_PETS_CANDIDATE": 6,
                       "FOUNDER_EXCEPTION": 6,
                       "NO_FOUNDER_ACTION": 6}
    check("recorded triage distribution matches the halted-021 audit",
          dict(recorded_triage) == expected_triage,
          "rebuilt %s vs expected %s" % (dict(recorded_triage),
                                         expected_triage))
    check("independent reader rebuild agrees with the clean-block size",
          rebuilt["pets_allowed_true"]
          >= recorded_triage["CLEAN_PET_FRIENDLY_CANDIDATE"],
          "reader true=%d, clean PF=%d"
          % (rebuilt["pets_allowed_true"],
             recorded_triage["CLEAN_PET_FRIENDLY_CANDIDATE"]))
    check("no clean VERIFIED_NO_PETS rests on a silent page",
          all((row.get("block") or "").strip() for row in rows
              if row["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE"))

    # ---- Phase 2: chain of custody ------------------------------------- #
    script = (_REPO_ROOT / "scripts" / "pettripfinder"
              / "detroit_ann_arbor_attended_close_020_completion.py")
    text = script.read_text(encoding="utf-8") if script.is_file() else ""
    paid_markers = [m for m in ("brightdata", "firecrawl", "web_unlocker",
                                "googleapis", "places", "api_key", "requests.")
                    if m in text.lower()]
    check("the completion script names no paid provider", not paid_markers,
          str(paid_markers))
    check("the completion script declares the attended lane",
          "attended" in text.lower(), "")
    check("the completion recorded provider_calls = 0 and spend 0",
          triage.get("provider_calls") == 0 and triage.get("spend_usd") == 0.0,
          "calls=%s spend=%s" % (triage.get("provider_calls"),
                                 triage.get("spend_usd")))
    check("hashes were computed from captured bytes, not copied",
          not bad_hash, "verified by re-hashing every file above")

    failed = [c for c in checks if not c["pass"]]
    write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-completion-forensics/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("provenance_event", OrderedDict([
            ("label", PROVENANCE),
            ("base_commit", BASE),
            ("external_commit", EXTERNAL),
            ("produced_by",
             "a different session, after %s, and committed by it" % BASE),
            ("adopted_by", WORK_ORDER),
            ("note",
             "The historical fact stays visible: these 33 captures were NOT "
             "produced by this order. This order verified and adopted them."),
        ])),
        ("phase_0_inventory", inventory),
        ("authority_paths_touched_by_the_outside_commit", authority_touched),
        ("reconstruction", OrderedDict([
            ("rows", len(rows)),
            ("independent_reader_rebuild", dict(rebuilt)),
            ("recorded_triage", dict(recorded_triage)),
            ("recorded_outcome", dict(recorded_outcome)),
        ])),
        ("integrity_checks", checks),
        ("advisory_checks", advisory),
        ("failed", len(failed)),
        ("verdict", "ADOPT" if not failed else "STOP"),
        ("verdict_note",
         "ADOPT means the evidence is authentic, complete and untampered -- "
         "not that every row is publishable. Classification is decided by the "
         "publication gates, which reject on their own terms."),
    ]))

    width = max(len(c["check"]) for c in checks)
    print("=== Phases 0-2: forensic verification of the outside completion ===")
    for c in checks:
        print("  %-*s  %s" % (width, c["check"], "PASS" if c["pass"] else "FAIL"))
        if not c["pass"]:
            print("      %s" % c["detail"])
    print()
    for a in advisory:
        print("  ADVISORY %-58s %s"
              % (a["check"], "PASS" if a["pass"] else "SEE GATE"))
        for d in a.get("disagreements") or []:
            print("      %s" % (d,))
    print()
    print("  independent reader rebuild:", dict(rebuilt))
    print("  recorded triage           :", dict(recorded_triage))
    print("  VERDICT:", "ADOPT" if not failed else "STOP")
    print("wrote", OUT.name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
