"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- correct the live rows the repaired reader exposes.

    python -m scripts.pettripfinder.question_negation_live_correction_001            # dry run, writes nothing
    python -m scripts.pettripfinder.question_negation_live_correction_001 --write
    python -m scripts.pettripfinder.build_global_authority --write
    python -m scripts.pettripfinder.question_negation_live_correction_001 --contracts

WHAT WAS WRONG
--------------
The shared first-party reader read an FAQ QUESTION ("Are pets allowed?", "Is Honu Cove Pet Friendly?") as an
acceptance and could not read several refusal shapes ("pets (including ESAs) are not permitted", "we do not accept
pets", "a pet-free facility", "a strict no-pet policy", "is not a pet-friendly hotel"). So hotels whose own ANSWER
refuses pets were published VERIFIED_PET_FRIENDLY, and two hotels whose page only ASKS the question were published
with nothing behind them. ``brightdata.policy_reading`` is repaired in this order; this module applies the repaired
reading to the live rows it moves, and to nothing else.

WHICH ROWS
----------
Exactly the rows ``live_pet_policy_quote_safety_scan_001`` found moving out of acceptance under the repaired
reader (every live pet-friendly record of every live market was scanned). Each is listed below BY IDENTITY with the
action the order prescribes, and ``plan`` refuses to run unless the committed scan names exactly this set:

  REFUSE  the row's own first-party quote explicitly refuses ordinary pets. It leaves the pet-friendly cohort and
          enters the market's VERIFIED_NO_PETS exclusions through the canonical exclusion builder
          (``market_registration_cli.exclusion_record``, whose hashes ``hotel_exclusions`` derives), citing the
          refusal sentence VERBATIM from the row's own capture. The repaired reader must read that sentence as a
          refusal (``first_party_binding.classify_quote`` kind no_pets == ELIGIBLE) or nothing is written.
  HOLD    the only "acceptance" was the question. No separate affirmative first-party evidence exists in the
          market's own captures, so the row leaves publication and is held (AWAITING_POLICY_OBSERVATION /
          EVIDENCE_HOLD). It is NOT made no-pets: a question refuses nothing.
  REBIND  the question was the cited quote, but the SAME first-party capture states an acceptance in its answer.
          That sentence is bound as the operative pets_allowed quote and the row stays pet-friendly. The sentence
          must appear verbatim in the market's own committed capture for this identity and must be read as an
          acceptance by the repaired reader.

WHAT IT WRITES (per affected market, and only there)
-----------------------------------------------------
  the root policy package          the REFUSE / HOLD records removed; the REBIND quote rebound
  markets/authority/<m>/           seed rows for REFUSE / HOLD removed, REBIND pet_policy rebound; exclusions shard
                                   gains the REFUSE rows (canonical builder, sorted as every shard is)
  the final partition              each moved item's state, disposition and evidence; counts re-derived
  deploy/netlify/release_contracts the derived fields ONLY (policy package digest and count, public surface, route
                                   counts, reconciliation, final_partition block), re-derived by
                                   ``release_contracts.derive_authority`` and required to verify with 0 disagreements
  markets/reports/question_negation_live_correction_001.json   the ledger: every row, before and after, per market

The generated globals are then rebuilt by ``build_global_authority --write`` (the canonical builder), and because a
contract's verified-no-pets count derives from the GLOBAL exclusions, ``--contracts`` re-derives the seven contracts
once more over the rebuilt globals and restates the ledger's "after" counts. Every other market's bytes are
untouched. Nothing here deploys.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder import market_authority as MA  # noqa: E402
from scripts.pettripfinder import market_registration_cli as MRC  # noqa: E402
from scripts.pettripfinder import release_contracts as RC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as READER  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
AS_OF = "2026-09-30"
PKG = _REPO / "launch_packages" / "pettripfinder"
SCAN = PKG / "markets" / "reports" / "live_pet_policy_quote_safety_scan_001.json"
LEDGER = PKG / "markets" / "reports" / "question_negation_live_correction_001.json"

REFUSE, HOLD, REBIND = "REFUSE", "HOLD", "REBIND"

#: The rows, by market and identity. For REFUSE the value is the refusal sentence the exclusion cites (``None``: the
#: row's whole current quote, which the repaired reader already reads as a refusal). For REBIND it is the answer
#: sentence the same capture states. For HOLD it is the reason.
CORRECTIONS = OrderedDict([
    ("fort-lauderdale-fl", OrderedDict([
        ("dolphin hollywood", (REFUSE, None)),
        ("honu cove", (REFUSE, None)),
        ("mariner motel inc", (REFUSE, None)),
    ])),
    ("tampa-fl", OrderedDict([
        ("bellweather beach resort", (REFUSE, None)),
        ("bon aire motel apts", (REFUSE, None)),
        ("boutique beach retreat", (REFUSE, None)),
        ("crystal palms beach resort at treasure island", (REFUSE, None)),
        ("hotel south tampa and suites", (REFUSE, None)),
        ("sunset vistas beachfront suites", (REFUSE, None)),
    ])),
    ("san-diego-ca", OrderedDict([
        ("island palms hotel and marina", (REFUSE, None)),
        ("pacific terrace hotel", (REFUSE, None)),
    ])),
    ("jacksonville-fl", OrderedDict([
        # The captured answer refuses THIS complex and then points the guest at the operator's OTHER, dog-friendly
        # properties, so the whole quote reads as asserting and denying. The refusal sentence is its own.
        ("amelia surf and racquet club", (REFUSE, "The entire Surf & Racquet Club complex is a pet‑free "
                                                  "community and does not allow pets of any kind.")),
    ])),
    ("miami-fl", OrderedDict([
        ("clevelander south beach", (HOLD, "the property's own FAQ asks 'Are you pet-friendly?' and the capture "
                                          "states no answer; no other first-party capture of this identity states "
                                          "a policy")),
        ("essex house hotel", (HOLD, "the property's own FAQ asks 'Are pets allowed?' and answers only 'Please "
                                    "contact the hotel directly for the most up-to-date pet policy'; no other "
                                    "first-party capture of this identity states a policy")),
    ])),
    ("phoenix-az", OrderedDict([
        ("the scott resort and spa", (REBIND, "Yes, we allow our four legged friends to sleep in two buildings "
                                               "leaving the other three buildings pet-free.")),
    ])),
    ("orlando-fl", OrderedDict([
        ("vacation village at parkway", (REBIND, "We are one of the few resorts in the area that offers a limited "
                                                 "number of pet-friendly suites located in Buildings 5 and 6.")),
    ])),
])


class CorrectionError(RuntimeError):
    """A precondition the order sets did not hold; nothing is written."""


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _dump_json(doc):
    return (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def _flat(text):
    return " ".join(str(text or "").split())


def _contract(market):
    return _load(_REPO / "deploy" / "netlify" / "release_contracts" / ("%s.json" % market))


def _captured_pages(market, key):
    """Every page the market's own committed capture lanes persisted for ``key``.

    Returns ``(row_sha, page_url, page_sha, sentences)``. ``row_sha`` is the capture row's own digest (``h``): a lane
    that follows a property's FAQ link records the sentences per page but binds the row, so a package entry cites the
    row digest for a sentence its FAQ page states. A lane that stores one quote (``q``) states it as one sentence.
    """
    out = []
    raw = PKG / "markets" / "staging" / market / "raw_captures"
    for path in sorted(raw.glob("*.json*")):
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            doc = json.loads(text)
            rows = doc.get("rows") if isinstance(doc, dict) else doc
        for row in rows or ():
            if not isinstance(row, dict) or row.get("identity_key") != key:
                continue
            row_sha = row.get("h") or row.get("sha256") or ""
            for page in row.get("pages") or ():
                out.append((row_sha, page.get("url"), page.get("sha256"),
                            [_flat(s) for s in page.get("pet_sentences") or ()]))
            loose = [_flat(s) for s in (row.get("sentences") or ()) if isinstance(s, str)]
            if row.get("q"):
                loose.append(_flat(row["q"]))
            if loose:
                out.append((row_sha, row.get("final_url") or row.get("u"), row_sha, loose))
    return out


def _pets_allowed_entry(record):
    entries = [e for e in record.get("evidence") or () if e.get("field") == "pets_allowed"
               and e.get("artifact_class") == "PUBLICATION_GRADE_EVIDENCE"]
    if len(entries) != 1:
        raise CorrectionError("%s: expected exactly one publication-grade pets_allowed entry, found %d"
                              % (record.get("identity_key"), len(entries)))
    return entries[0]


def _scan_defects():
    scan = _load(SCAN)
    return {(r["market_id"], r["identity_key"]): r for r in scan["defects"]
            if r["class_before"] == "AFFIRMATIVE_ACCEPTANCE"}


def plan():
    """Validate every correction against the committed scan and the repaired reader; write nothing."""
    defects = _scan_defects()
    planned = {(m, k) for m, rows in CORRECTIONS.items() for k in rows}
    if planned != set(defects):
        raise CorrectionError("the correction list must be exactly the scan's moved rows: missing %s, extra %s"
                              % (sorted(set(defects) - planned), sorted(planned - set(defects))))
    out = OrderedDict()
    for market, rows in CORRECTIONS.items():
        pkg = _load(_REPO / _contract(market)["policy_package"]["path"])
        by_key = {h["identity_key"]: h for h in pkg["hotels"]}
        items = []
        for key, (action, detail) in rows.items():
            record = by_key.get(key)
            if record is None or record["facts"].get("pets_allowed") is not True:
                raise CorrectionError("%s/%s is not a live pet-friendly record" % (market, key))
            entry = _pets_allowed_entry(record)
            quote = _flat(entry["quote"])
            ctx = " ".join(dict.fromkeys(_flat(e.get("quote")) for e in record["evidence"]
                                         if e is not entry and e.get("artifact_sha256") == entry.get("artifact_sha256")))
            now_pf = FPB.classify_quote(quote, kind=FPB.KIND_PET_FRIENDLY, context=ctx)[0]
            if now_pf == FPB.ELIGIBLE:
                raise CorrectionError("%s/%s still reads as an acceptance under the repaired reader" % (market, key))
            item = OrderedDict([("identity_key", key), ("name", record["name"]), ("action", action),
                                ("quote_before", quote), ("classify_before_repair", "ELIGIBLE (acceptance)"),
                                ("classify_after_repair", now_pf)])
            if action == REFUSE:
                refusal = _flat(detail) if detail else quote
                if refusal not in quote:
                    raise CorrectionError("%s/%s: the refusal sentence is not verbatim in the row's own quote"
                                          % (market, key))
                cls = FPB.classify_quote(refusal, kind=FPB.KIND_NO_PETS)[0]
                if cls != FPB.ELIGIBLE or READER.parse(refusal).pets_allowed is not False:
                    raise CorrectionError("%s/%s: the repaired reader does not read %r as a refusal (%s)"
                                          % (market, key, refusal, cls))
                item["refusal_quote"] = refusal
                item["refusal_context"] = quote
            elif action == HOLD:
                if READER.parse(quote).pets_allowed is False:
                    raise CorrectionError("%s/%s reads as a refusal; it is a REFUSE row, not a HOLD" % (market, key))
                pages = _captured_pages(market, key)
                affirmative = [s for _r, _u, _h, sents in pages for s in sents
                               if FPB.classify_quote(s, kind=FPB.KIND_PET_FRIENDLY)[0] == FPB.ELIGIBLE]
                if affirmative:
                    raise CorrectionError("%s/%s: the market's own capture states an acceptance %r -- REBIND, not "
                                          "HOLD" % (market, key, affirmative[0]))
                item["hold_reason"] = detail
                item["captured_pages_searched"] = len(pages)
            else:
                sentence = _flat(detail)
                cited = str(entry.get("artifact_sha256") or "").split(":", 1)[-1]
                pages = [(u, h, sents) for r, u, h, sents in _captured_pages(market, key)
                         if sentence in sents and cited in (r, h)]
                if not pages:
                    raise CorrectionError("%s/%s: %r is not verbatim in the capture the record already cites (%s)"
                                          % (market, key, sentence, cited))
                page_url, _page_sha, block = pages[0]
                cls = FPB.classify_quote(sentence, kind=FPB.KIND_PET_FRIENDLY, context=" ".join(block))[0]
                if cls != FPB.ELIGIBLE:
                    raise CorrectionError("%s/%s: the answer %r is not an operative acceptance (%s)"
                                          % (market, key, sentence, cls))
                item["rebind_quote"] = sentence
                item["rebind_page_url"] = page_url
                item["artifact_sha256"] = entry.get("artifact_sha256")
            items.append(item)
        out[market] = items
    return out


def _counts(market):
    d = RC.derive_authority(market)
    return OrderedDict([("pet_friendly", d.published_hotel_profiles), ("verified_no_pets", d.verified_no_pets),
                        ("unresolved_held", d.unresolved), ("hotel_routes", d.hotel_route_count),
                        ("corridor_routes", d.corridor_route_count)])


def apply(market, items):
    """Rewrite one market's package, shard, partition and contract for the planned items."""
    contract = _contract(market)
    pkg_path = _REPO / contract["policy_package"]["path"]
    part_path = _REPO / contract["final_partition"]["path"]
    pkg = _load(pkg_path)
    part = _load(part_path)
    ex_doc = _load(MA.exclusions_shard_path(market))
    seed_raw = MA.seed_shard_path(market).read_text(encoding="utf-8")
    seed = list(csv.DictReader(io.StringIO(seed_raw)))
    census = {h["identity_key"]: h for h in _load(PKG / "identity_census" / ("%s.json" % market))["hotels"]}
    by_item = {i["identity_key"]: i for i in items}

    def seed_index(name):
        hits = [n for n, r in enumerate(seed) if normalize_name(r["name"]) == normalize_name(name)
                and r.get("category") == "pet-friendly-hotels"]
        if len(hits) != 1:
            raise CorrectionError("%s: %d seed rows join %r" % (market, len(hits), name))
        return hits[0]

    new_exclusions = []
    source = OrderedDict([
        ("work_order", WORK_ORDER),
        ("ledgers", [LEDGER.relative_to(_REPO).as_posix(), SCAN.relative_to(_REPO).as_posix()]),
        ("decided_by", WORK_ORDER),
        ("decision_basis", "the founder's work order directs every live pet-friendly row whose own first-party quote "
                           "explicitly refuses ordinary pets into the canonical verified-no-pets path; this exclusion "
                           "restates that directive for this row, cites the property's own refusal verbatim, and adds "
                           "no finding of its own"),
    ])
    kept = []
    for record in pkg["hotels"]:
        item = by_item.get(record["identity_key"])
        if item is None:
            kept.append(record)
            continue
        entry = _pets_allowed_entry(record)
        row = seed[seed_index(record["name"])]
        if item["action"] == REFUSE:
            auth = OrderedDict([
                ("exclusion_id", "%s--%s" % (market, re.sub(r"[^a-z0-9]+", "-", normalize_name(record["name"]))
                                             .strip("-"))),
                ("normalized_name", record["identity_key"]),
                ("canonical_name", record["name"]),
                ("address", row["address"]), ("city", row["city"]), ("state", row["state"]),
                ("postal_code", row["postal_code"]),
                ("official_url", row.get("website_url") or entry["source_url"]),
                ("exclusion_state", "VERIFIED_NO_PETS"),
                ("evidence_quote", item["refusal_quote"]),
                ("evidence", [OrderedDict([("quote", item["refusal_context"])])]),
                ("source_url", entry["source_url"]),
                ("observed_at", str(entry.get("captured_at") or "")[:10]),
                ("snapshot_hash", str(entry["artifact_sha256"]).split(":", 1)[-1]),
                ("founder_reviewer_id", WORK_ORDER),
                ("founder_reviewed_at", AS_OF),
            ])
            new_exclusions.append(MRC.exclusion_record(auth, census.get(record["identity_key"], {}), market,
                                                       decision_source=source))
            seed.pop(seed_index(record["name"]))
        elif item["action"] == HOLD:
            seed.pop(seed_index(record["name"]))
        else:
            # The same artifact, the same source URL the record already cites: only the sentence changes, from the
            # question to the answer the same capture states.
            entry["quote"] = item["rebind_quote"]
            row["pet_policy"] = item["rebind_quote"]
            kept.append(record)
    pkg["hotels"] = kept

    exclusions = sorted(ex_doc["exclusions"] + new_exclusions, key=lambda e: e["normalized_name"])
    ids = Counter(e["exclusion_id"] for e in exclusions)
    if any(v > 1 for v in ids.values()):
        raise CorrectionError("%s: duplicate exclusion ids %s" % (market, [k for k, v in ids.items() if v > 1]))

    for it in part["items"]:
        item = by_item.get(it["identity_key"])
        if item is None:
            continue
        ev = it.get("evidence") or OrderedDict()
        if item["action"] == REFUSE:
            it["final_state"], it["disposition"], it["resolved"] = "VERIFIED_NO_PETS", "CLEAN_VERIFIED_NO_PETS", True
            it.pop("policy_facts", None)
            ev["pets_allowed_claim"] = False
            ev["quote"] = item["refusal_quote"]
        elif item["action"] == HOLD:
            it["final_state"], it["disposition"], it["resolved"] = "AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD", False
            it.pop("policy_facts", None)
            ev["pets_allowed_claim"] = None
            it["next_action_source"] = WORK_ORDER
            it["determined_by"] = WORK_ORDER
            it["next_action"] = ("QUESTION_ONLY -- %s; a question is never an acceptance and never a refusal"
                                 % item["hold_reason"])
        else:
            ev["quote"] = item["rebind_quote"]
        it["evidence"] = ev
        it["corrected_by"] = WORK_ORDER
    part["counts_by_state"] = OrderedDict(sorted(Counter(i["final_state"] for i in part["items"]).items()))
    part["counts_by_disposition"] = OrderedDict(sorted(Counter(i["disposition"] for i in part["items"]).items()))
    part["resolved"] = sum(1 for i in part["items"] if i.get("resolved"))
    part["unresolved"] = sum(1 for i in part["items"] if not i.get("resolved"))

    writes = [
        (pkg_path, _dump_json(pkg)),
        (part_path, _dump_json(part)),
        (MA.exclusions_shard_path(market), MA.render_json(MA.build_exclusions_shard(market, exclusions)).encode("utf-8")),
        (MA.seed_shard_path(market), MA.render_seed_csv(seed).encode("utf-8")),
    ]
    for path, data in writes:
        Path(path).write_bytes(data)
    return [Path(p).relative_to(_REPO).as_posix() for p, _d in writes]


def rederive_contract(market):
    """Only the DERIVED fields; every descriptive field is kept; must then verify with 0 disagreements."""
    path = _REPO / "deploy" / "netlify" / "release_contracts" / ("%s.json" % market)
    contract = _load(path)
    d = RC.derive_authority(market)
    contract["policy_package"]["expected_sha256"] = d.policy_package_sha256
    contract["policy_package"]["expected_record_count"] = d.policy_package_record_count
    surface = contract["public_surface"]
    surface["public_hotel_profile_count"] = d.published_hotel_profiles
    surface["excluded_public_profile_count"] = d.excluded_public_profiles
    surface["seed_hotel_rows"] = d.seed_hotel_rows
    contract["routes"]["hotel_route_count"] = d.hotel_route_count
    contract["routes"]["published_corridor_route_count"] = d.corridor_route_count
    recon = contract["reconciliation"]
    before = OrderedDict((f, recon.get(f)) for f in ("published_pet_friendly", "verified_no_pets", "unresolved"))
    for field, value in d.reconciliation().items():
        recon[field] = value
    # The note states the counts in prose; restate the correction beside it rather than leave a stale number
    # unexplained. Idempotent: a second run over the corrected contract changes nothing.
    marker = " CORRECTED by %s:" % WORK_ORDER
    note = str(recon.get("note") or "")
    if marker not in note and any(before[f] != recon.get(f) for f in before):
        recon["note"] = note + ("%s the repaired first-party reader moved this market to %d pet-friendly / %d "
                                "verified-no-pets / %d unresolved (was %d / %d / %d); every moved row is named in "
                                "%s." % (marker, recon["published_pet_friendly"], recon["verified_no_pets"],
                                         recon["unresolved"], before["published_pet_friendly"],
                                         before["verified_no_pets"], before["unresolved"],
                                         LEDGER.relative_to(_REPO).as_posix()))
    block = contract["final_partition"]
    fresh = RC.final_partition_block(market, block["path"].split("/")[-1], note=block.get("note"))
    for k in ("path", "schema", "expected_sha256", "expected_count"):
        block[k] = fresh[k]
    path.write_bytes(_dump_json(contract))
    problems = RC.verify_contract(market)
    if problems:
        raise CorrectionError("%s: release contract disagrees after re-derivation: %s" % (market, problems))
    return path.relative_to(_REPO).as_posix()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--contracts", action="store_true",
                    help="after build_global_authority --write: re-derive the contracts and the ledger's after counts")
    args = ap.parse_args(argv)
    if args.contracts:
        ledger = _load(LEDGER)
        for market, entry in ledger["markets"].items():
            rederive_contract(market)
            entry["after"] = _counts(market)
            print(market, "before", dict(entry["before"]), "after", dict(entry["after"]))
        LEDGER.write_bytes(_dump_json(ledger))
        return 0
    planned = plan()
    for market, items in planned.items():
        for it in items:
            print("%-20s %-7s %-44s %s" % (market, it["action"], it["name"][:44],
                                          (it.get("refusal_quote") or it.get("rebind_quote") or it.get("hold_reason"))[:90]))
    if not args.write:
        print("dry run: %d rows in %d markets planned; nothing written" % (sum(len(v) for v in planned.values()),
                                                                           len(planned)))
        return 0
    ledger = OrderedDict([("schema", "ptf-live-correction-ledger/1.0"), ("work_order", WORK_ORDER), ("as_of", AS_OF),
                          ("scan", SCAN.relative_to(_REPO).as_posix()), ("markets", OrderedDict())])
    for market, items in planned.items():
        before = _counts(market)
        written = apply(market, items)
        written.append(rederive_contract(market))
        after = _counts(market)
        ledger["markets"][market] = OrderedDict([("before", before), ("after", after), ("rows", items),
                                                 ("written", written)])
        print(market, "before", dict(before), "after", dict(after))
    LEDGER.write_bytes(_dump_json(ledger))
    print("ledger", LEDGER.relative_to(_REPO).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
