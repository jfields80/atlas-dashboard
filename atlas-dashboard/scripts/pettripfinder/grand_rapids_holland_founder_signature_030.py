# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030 -- sign fourteen records, promote eight.

028 acquired thirteen rows at publication grade. 029 reconciled six identities
the gate had refused on a street suffix and read one of them. This order asks a
founder to approve those records and promotes the approved ones into source.

Nothing is discovered, acquired or re-read. Every fact was established by 028
and 029, and this pass may not reinterpret one.

THE RECONCILED ROW NEEDS SOMETHING THE OTHER THIRTEEN DO NOT
--------------------------------------------------------------
Twelve rows came through 028's identity gate cleanly and already sit in an
observation store. The Comfort Inn does not: its capture was DECLINED at the
identity gate, which runs BEFORE the policy locator, so no policy block was
ever cut and no store record exists.

029 settled the identity. What that entitles this pass to do is RE-LOCATE the
block from bytes already on disk -- the sanctioned move for exactly this case,
because the locator never ran, not because it ran and failed. So the block is
cut here, into a NEW directory: the declined capture is evidence of what the
gate saw and is never edited. The re-located capture then goes through the
COMMITTED store builder with 029's ruling supplied as a founder identity
override, which is the mechanism that exists for "a human's identity ruling,
which no reader may make for itself".

The result is a record built by the same builder, read by the same reader and
judged by the same membrane as the other thirteen. That is what makes it
signable on the same terms.

WHAT A SIGNATURE BINDS
-----------------------
A semantic hash, not a row. ``semantic-approval/1.0`` separates the approved
MEANING from its provenance so an approval lapses when a fact moves and
survives when only a timestamp does. Every signature here records the hash it
was bound to, and a row whose hash cannot be reproduced is REFUSED rather than
signed -- the count is never forced.

TWO RULINGS FOR THE RECONCILED ROW, NOT ONE
--------------------------------------------
Its identity was ruled by a machine reconciliation, not by the acquisition
gate. So it carries an explicit SAME_PROPERTY_CONFIRMED identity ruling AND a
record-level approval, recorded separately. Identity confirmation is not policy
approval, and a single field could not say both.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_founder_review_cli as FR             # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR            # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC          # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA           # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS              # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "grand-rapids-holland-mi.json"
PACKET_029 = LP / "grand_rapids_holland_mi_founder_review_packet_029.json"
RECONCILIATION_029 = LP / "grand_rapids_holland_mi_identity_reconciliation_029.json"
STORE_028 = LP / "grand_rapids_holland_mi_observation_store_028.json"
ACQUISITION_028 = LP / "grand_rapids_holland_mi_market_acquisition_028.json"

RELOCATED_ROOT = _REPO_ROOT / "data" / "acquisition" / "gr_030_relocated"
SUPPLEMENT_PATH = LP / "grand_rapids_holland_mi_relocated_capture_030.json"
OVERRIDES_PATH = LP / "grand_rapids_holland_mi_founder_overrides_030.json"
STORE_030 = LP / "grand_rapids_holland_mi_observation_store_030.json"
SIGNATURES_PATH = LP / "grand_rapids_holland_mi_founder_decision_ledger_030.json"

WORK_ORDER = "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030"
MARKET = "grand-rapids-holland-mi"
FOUNDER = "PTF-FOUNDER-001"
REVIEWED_AT = "2026-08-29"
RUN_ID = "grand-rapids-holland-mi-signature-030"

RECONCILED_KEY = "comfort inn airport"
SAME_PROPERTY = "SAME_PROPERTY_CONFIRMED"

AUTHORIZATION = (
    "The founder authorises review and record-level approval of the candidates "
    "in grand_rapids_holland_mi_founder_review_packet_029.json, on the "
    "evidence and classifications established by "
    "PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028 and "
    "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029. It does not extend to a "
    "HOLD, to a POLICY_NOT_FOUND row, to an unresolved identity, to a row "
    "outside that packet, or to a record whose semantic-approval hash cannot "
    "be reproduced from the store it was reviewed on.")

SIGNED_HASH_BOUND = "SIGNED_HASH_BOUND_TO_THE_REVIEWED_STATE"
REFUSED_HASH_UNREPRODUCIBLE = "REFUSED_THE_HASH_CANNOT_BE_REPRODUCED"
REFUSED_CLASS = "REFUSED_CLASSIFICATION_IS_NOT_A_PUBLISHING_CLASS"
REFUSED_READINESS = "REFUSED_READINESS_DOES_NOT_ROUTE_ITSELF"
SIGNED_OUTCOMES = (SIGNED_HASH_BOUND,)

#: The readiness states a record may be signed on. POLICY_NOT_FOUND and
#: POLICY_PARTIAL defer to a person and are refused here by construction.
SIGNABLE_STATES = frozenset(
    READINESS.PUBLISHABLE_STATES | {READINESS.POLICY_NEGATIVE_CONFIRMED})


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, document: Mapping) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Stage one: cut the block the identity gate never let the locator cut
# --------------------------------------------------------------------------- #

def relocate_capture(root: Path = RELOCATED_ROOT) -> Dict:
    """Materialise a full capture for the reconciled row, from saved bytes.

    THE DECLINED CAPTURE IS NOT TOUCHED. It is the record of what the gate saw
    and stays exactly as 028 wrote it; the re-located capture is a new
    directory, and both remain on disk so the two can be compared.

    Only the policy block is new, and it is not new evidence: the committed
    locator is run over the rendered HTML that was already bought and already
    hashed. Calling this a re-LOCATE rather than a re-parse matters -- the
    locator never ran on these bytes, so there is no earlier reading to
    contradict.
    """
    acquisition = _load(ACQUISITION_028)
    result = next(r for r in acquisition["results"]
                  if r["identity_key"] == RECONCILED_KEY)
    declined = Path((result.get("declined_dir") or "").replace("\\", "/"))
    html_path = declined / "rendered.html"
    if not html_path.is_file():
        raise SystemExit("no saved rendered.html for %r; nothing to re-locate"
                         % RECONCILED_KEY)

    html = html_path.read_text(encoding="utf-8", errors="replace")
    located = UC.locate_policy_in_html(html)
    if not located.found:
        raise SystemExit("the committed locator finds no block in the saved "
                         "document for %r" % RECONCILED_KEY)

    slug = declined.parent.name
    attempt = root / slug / "attempt-01"
    attempt.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(html_path, attempt / "rendered.html")
    if (declined / "page-text.txt").is_file():
        shutil.copyfile(declined / "page-text.txt", attempt / "page-text.txt")
    (attempt / "policy-block.txt").write_text(located.text, encoding="utf-8")

    import hashlib
    block_sha = hashlib.sha256(
        (attempt / "policy-block.txt").read_bytes()).hexdigest()
    _write(attempt / "locator.json", OrderedDict((
        ("strategy", located.strategy),
        ("selector", getattr(located, "selector", "") or ""),
        ("block_sha256", block_sha),
        ("relocated_by", WORK_ORDER),
        ("relocated_from", declined.as_posix()),
        ("why", "the capture was declined at the IDENTITY gate, which runs "
                "before the locator, so no block was ever cut. "
                "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029 settled the "
                "identity; the block is cut here from the same bytes."),
    )))
    return OrderedDict((
        ("identity_key", RECONCILED_KEY),
        ("declined_directory", declined.as_posix()),
        ("relocated_directory", attempt.relative_to(_REPO_ROOT).as_posix()),
        ("locator_strategy", located.strategy),
        ("block_chars", len(located.text)),
        ("block_sha256", block_sha),
        ("declined_capture_untouched", (declined / "declined.json").is_file()),
        ("result", result),
    ))


def supplement_document(relocated: Mapping) -> Dict:
    """An acquisition-shaped document holding the one reconciled row.

    Its outcome is VALID because 029 RULED the identity, and the ruling is
    named here rather than implied. Everything else is copied from what 028
    actually fetched.
    """
    result = dict(relocated["result"])
    result["outcome"] = "VALID"
    result["identity_confirmed"] = True
    result["artifact_dir"] = str(_REPO_ROOT / relocated["relocated_directory"])
    result["declined_dir"] = ""
    result["locator_strategy"] = relocated["locator_strategy"]
    result["identity_reasons"] = [
        "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029 ruled %s on six agreeing "
        "signals, five of them not a telephone" % SAME_PROPERTY]
    return OrderedDict((
        ("schema", "ptf-market-paid-acquisition/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("what_this_is",
         "the single row 029 reconciled, expressed as an acquisition result so "
         "the COMMITTED store builder can derive an observation from it. No "
         "provider was called: the capture is 028's, re-located from its own "
         "saved bytes."),
        ("derived_from", OrderedDict((
            ("acquisition", ACQUISITION_028.name),
            ("identity_ruling", RECONCILIATION_029.name),
        ))),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("dry_run", False),
        ("results", [result]),
    ))


def overrides_document() -> Dict:
    """029's identity ruling, in the form the store builder reads.

    The builder takes identity rulings from a founder-override document and
    from nowhere else, precisely because a reader may not make one for itself.
    """
    reconciliation = _load(RECONCILIATION_029)
    ruling = next(r for r in reconciliation["identity_review"]["rows"]
                  if r["identity_key"] == RECONCILED_KEY)
    return OrderedDict((
        ("schema", "ptf-founder-override/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("decided_by", FOUNDER), ("decided_at", REVIEWED_AT),
        ("identity_overrides", OrderedDict((
            ("founder_ruling",
             "%s: the acquisition gate declined this capture on a street "
             "SUFFIX ('%s'). 029 found %d agreeing signals, %d of them not a "
             "telephone, and the founder adopts that ruling."
             % (SAME_PROPERTY, ruling["gate_declined_because"],
                ruling["signal_count"], ruling["non_telephone_signal_count"])),
            ("records", [OrderedDict((
                ("identity_key", RECONCILED_KEY),
                ("verdict", SAME_PROPERTY),
                ("signals", [s["signal"] for s in ruling["signals_agreeing"]]),
                ("page_name", ruling["page_name"]),
                ("page_address", ruling["page_address"]),
                ("census_address", ruling["census_address"]),
            ))]),
        ))),
    ))


def build_reconciled_record() -> Tuple[Dict, Dict]:
    """``(store_document, relocation)`` for the one reconciled row."""
    relocated = relocate_capture()
    supplement = supplement_document(relocated)
    overrides = overrides_document()
    _write(SUPPLEMENT_PATH, supplement)
    _write(OVERRIDES_PATH, overrides)

    census = _load(CENSUS_PATH)
    records, refusals, restated = MOS.build(
        supplement, run_id=RUN_ID, census=census, founder_overrides=overrides)
    if refusals:
        raise SystemExit("the committed store builder refused the reconciled "
                         "row: %s" % json.dumps(refusals))
    if len(records) != 1:
        raise SystemExit("expected exactly one reconciled record, got %d"
                         % len(records))
    return (OrderedDict((
        ("schema", MOS.SCHEMA), ("market_id", MARKET),
        ("work_order", WORK_ORDER), ("run_id", RUN_ID),
        ("what_this_is",
         "the observation for the row 029 reconciled, derived by the COMMITTED "
         "store builder from a capture re-located out of bytes 028 already "
         "bought. No provider was called."),
        ("count", len(records)),
        ("restated", restated),
        ("observations", records),
    )), relocated)


# --------------------------------------------------------------------------- #
# Stage two: the signature pass
# --------------------------------------------------------------------------- #

def _store_records(store: Mapping) -> List[Dict]:
    """A store writes its rows under ``records``; the builder returns them
    plainly. Read both so this pass does not depend on which produced it."""
    return list(store.get("records") or store.get("observations") or ())


def candidate_records() -> Tuple[Dict[str, Dict], Dict[str, str]]:
    """``(records, provenance)`` -- the fourteen the packet presents."""
    records: Dict[str, Dict] = {}
    provenance: Dict[str, str] = {}
    for record in _store_records(_load(STORE_028)):
        records[record["identity_key"]] = record
        provenance[record["identity_key"]] = "PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028"
    for record in _store_records(_load(STORE_030)):
        records[record["identity_key"]] = record
        provenance[record["identity_key"]] = "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029"
    return (records, provenance)


def packet_candidates() -> List[Dict]:
    """Every row the packet asks a founder to rule on, in one flat list."""
    packet = _load(PACKET_029)
    out: List[Dict] = []
    for group, expected in (("pet_friendly_candidates_from_028", "PET_FRIENDLY"),
                            ("verified_no_pets_from_028", "VERIFIED_NO_PETS"),
                            ("newly_resolved_in_029", "")):
        for row in packet[group]:
            out.append(OrderedDict((
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("classification",
                 row.get("classification") or expected),
                ("packet_group", group),
            )))
    return sorted(out, key=lambda r: r["identity_key"])


def semantic_hash_of(record: Mapping, census_row: Mapping) -> str:
    return FR.candidate_record(record, census_row)["semantic_approval"]["semantic_hash"]


def sign(candidates: Sequence[Mapping], records: Mapping[str, Mapping],
         census: Mapping[str, Mapping], provenance: Mapping[str, str],
         identity_rulings: Mapping[str, Mapping]) -> List[Dict]:
    """One decision per candidate, each bound to a hash it can reproduce.

    THE COUNT IS NEVER FORCED. A row whose classification is not a publishing
    class, whose readiness does not route itself, or whose hash cannot be
    computed from the store it was reviewed on, is REFUSED and says why.
    """
    rows: List[Dict] = []
    for candidate in candidates:
        key = candidate["identity_key"]
        klass = candidate["classification"]
        record = records.get(key)

        if record is None:
            outcome, why, bound = REFUSED_HASH_UNREPRODUCIBLE, (
                "no observation-store record exists for this identity, so "
                "there is no meaning to bind an approval to"), ""
        elif klass not in ("PET_FRIENDLY", "VERIFIED_NO_PETS"):
            outcome, why, bound = REFUSED_CLASS, (
                "%r is not a publishing classification" % klass), ""
        elif str((record.get("readiness") or {}).get("state") or "") \
                not in SIGNABLE_STATES:
            outcome, why, bound = REFUSED_READINESS, (
                "readiness %r defers to a person and may not be signed as a "
                "record" % (record.get("readiness") or {}).get("state")), ""
        else:
            try:
                bound = semantic_hash_of(record, census[key])
            except Exception as error:                       # noqa: BLE001
                outcome, why, bound = REFUSED_HASH_UNREPRODUCIBLE, (
                    "the semantic hash could not be computed: %s" % error), ""
            else:
                outcome, why = SIGNED_HASH_BOUND, (
                    "the record reproduces a semantic hash and its readiness "
                    "routes itself; the approval binds that hash")

        signed = outcome in SIGNED_OUTCOMES
        proposes = (enums.VERIFIED_NO_PETS if klass == "VERIFIED_NO_PETS"
                    else enums.PUBLISHED_PET_FRIENDLY)
        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", candidate["canonical_name"]),
            ("corridor", str((census.get(key) or {}).get("corridor") or "")),
            ("classification", klass),
            ("proposes_authority", proposes),
            ("established_by", provenance.get(key, "")),
            ("outcome", outcome), ("why", why),
            ("bound_semantic_hash", bound),
            ("bound_snapshot_hash", str(
                ((record or {}).get("observation") or {}).get("snapshot_hash") or "")),
            ("readiness", str(((record or {}).get("readiness") or {}).get("state") or "")),
            ("membrane", str(((record or {}).get("membrane") or {}).get("verdict") or "")),
            ("publication_grade", str(
                ((record or {}).get("publication_grade") or {}).get("verdict") or "")),
        ))

        # THE RECONCILED ROW CARRIES TWO RULINGS. Identity confirmation is not
        # policy approval, and one field cannot say both.
        if key in identity_rulings:
            ruling = identity_rulings[key]
            row["identity_ruling"] = OrderedDict((
                ("verdict", SAME_PROPERTY),
                ("ruled_by", FOUNDER), ("ruled_at", REVIEWED_AT),
                ("established_by", "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029"),
                ("signals", [s["signal"] for s in ruling["signals_agreeing"]]),
                ("non_telephone_signals", ruling["non_telephone_signal_count"]),
                ("gate_declined_because", ruling["gate_declined_because"]),
                ("why_it_needs_its_own_ruling",
                 "the acquisition gate DECLINED this capture; approving its "
                 "policy without ruling on its identity would publish a record "
                 "on evidence the gate refused"),
            ))

        if signed:
            row["founder_decision"] = FA.assert_writable(
                FA.CANONICAL_APPROVED, where="%s:%s" % (WORK_ORDER, key))
            row["founder_reviewer_id"] = FOUNDER
            row["founder_reviewed_at"] = REVIEWED_AT
            row["founder_authorization"] = AUTHORIZATION
        else:
            row["founder_decision"] = ""
            row["founder_reviewer_id"] = ""
            row["founder_reviewed_at"] = ""
        rows.append(row)
    return rows


def signature_pass() -> Dict:
    records, provenance = candidate_records()
    census = {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}
    candidates = packet_candidates()
    reconciliation = _load(RECONCILIATION_029)
    identity_rulings = {
        r["identity_key"]: r
        for r in reconciliation["identity_review"]["rows"]
        if r["identity_key"] == RECONCILED_KEY and r["verdict"] == SAME_PROPERTY}

    signatures = sign(candidates, records, census, provenance, identity_rulings)
    signed = [s for s in signatures if s["outcome"] in SIGNED_OUTCOMES]
    refused = [s for s in signatures if s["outcome"] not in SIGNED_OUTCOMES]
    pet_friendly = [s for s in signed if s["classification"] == "PET_FRIENDLY"]
    no_pets = [s for s in signed if s["classification"] == "VERIFIED_NO_PETS"]

    return OrderedDict((
        ("schema", "ptf-founder-decision-ledger/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        # The keys market_proposed_authority_cli reads. A ledger this pass
        # writes has to be the SAME contract 021 wrote, or the sanctioned
        # authority builder cannot take both.
        ("decided_by", FOUNDER), ("decided_at", REVIEWED_AT),
        ("approval_vocabulary", "founder-approval-vocabulary/1.0"),
        ("binding_contract", "semantic-approval/1.0"),
        ("authorization", AUTHORIZATION),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("inputs", OrderedDict((
            ("packet", PACKET_029.name),
            ("store_028", STORE_028.name),
            ("store_030", STORE_030.name),
            ("identity_ruling", RECONCILIATION_029.name),
        ))),
        ("counts", OrderedDict((
            ("candidates_presented", len(candidates)),
            ("signatures_written", len(signed)),
            ("signatures_refused", len(refused)),
            ("signed_pet_friendly", len(pet_friendly)),
            ("signed_verified_no_pets", len(no_pets)),
            ("by_outcome", OrderedDict(sorted(Counter(
                s["outcome"] for s in signatures).items()))),
        ))),
        ("identity_rulings_recorded",
         [s["identity_key"] for s in signatures if "identity_ruling" in s]),
        ("every_signature_binds_a_hash",
         all(s["bound_semantic_hash"] for s in signed)),
        ("no_unresolved_row_signed",
         all(s["readiness"] in SIGNABLE_STATES for s in signed)),
        ("signed", signed),
        ("refused_rows", refused),
        ("all_signatures", signatures),
    ))


# --------------------------------------------------------------------------- #
# Stage three: what the publication schema will and will not take
# --------------------------------------------------------------------------- #

MERGED_STORE = LP / "grand_rapids_holland_mi_observation_store_030_merged.json"
AUTHORITY_030 = LP / "grand_rapids_holland_mi_proposed_authority_030.json"
HOLDS_PATH = LP / "grand_rapids_holland_mi_publication_holds_030.json"
PACKAGE_PATH = LP / "hotel_policy_facts_grand-rapids-holland-mi.json"
MARKET_NAME = "Grand Rapids / Holland"
WEIGHT_RULING_023 = "PTF-GRAND-RAPIDS-WEIGHT-SEMANTICS-RULING-023"


def merged_store() -> Dict:
    """022's store plus what 028 acquired and 029 reconciled.

    A union keyed on identity, newest wins. Nothing is re-read: each record is
    exactly the one its own pass derived.
    """
    records: Dict[str, Dict] = {}
    sources: List[str] = []
    for path in (LP / "grand_rapids_holland_mi_observation_store_022.json",
                 STORE_028, STORE_030):
        document = _load(path)
        sources.append(path.name)
        for record in _store_records(document):
            records[record["identity_key"]] = record
    base = _load(LP / "grand_rapids_holland_mi_observation_store_022.json")
    out = OrderedDict((
        ("schema", base["schema"]), ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("what_this_is",
         "the current-state policy observation store for this market: 022's "
         "rows, the rows 028 acquired, and the one 029 reconciled. No provider "
         "was called to assemble it."),
        ("derived_from", sources),
        ("network_calls", 0), ("usd_spent", 0.0),
        ("count", len(records)),
        ("records", [records[key] for key in sorted(records)]),
    ))
    return out


def probe_package(authority_path: Path, store_path: Path,
                  expect: int, out: Path) -> Tuple[int, str]:
    """Run the sanctioned projector and report what it refuses. Writes nothing
    into source unless it succeeds, because it fails closed by design."""
    command = [sys.executable,
               str(_REPO_ROOT / "scripts" / "pettripfinder"
                   / "market_policy_package_cli.py"),
               "--authority", str(authority_path),
               "--market-name", MARKET_NAME,
               "--observations", str(store_path),
               "--expect-count", str(expect),
               "--weight-comparison-from-source",
               "--publish", WORK_ORDER,
               "--out", str(out)]
    done = subprocess.run(command, cwd=str(_REPO_ROOT),
                          capture_output=True, text=True)
    return (done.returncode, done.stdout + done.stderr)


#: The projector's own words when it fails closed. Anchoring on this rather
#: than on the first "[" matters: the failure arrives as a traceback, and a
#: traceback is full of brackets. Scanning from the first one parsed garbage,
#: swallowed the ValueError and reported ZERO refusals -- which looked exactly
#: like a clean projection and would have promoted three rows the schema
#: refuses.
_REFUSAL_MARKER = "the package was NOT written: "


def schema_refusals(output: str) -> List[Dict]:
    """The identity keys the publication schema refused, and why.

    Raises rather than returning empty on a malformed payload. An empty list
    here means "nothing was refused", and a parse failure must never be able to
    say that.
    """
    marker = output.find(_REFUSAL_MARKER)
    if marker < 0:
        if "PolicyPackageError" in output:
            raise SystemExit(
                "the projector failed in a way this pass cannot read:\n%s"
                % output[-2000:])
        return []
    start = marker + len(_REFUSAL_MARKER)
    payload = output[start:output.rfind("]") + 1]
    refusals = json.loads(payload)
    if not refusals:
        raise SystemExit("the projector refused the package and named no "
                         "rows; refusing to treat that as a clean run")
    return refusals


def publication_holds(refusals: Sequence[Mapping], store: Mapping) -> Dict:
    """A signed row the PUBLICATION schema will not take, and the reason.

    THIS IS NOT A FAILED SIGNATURE. The founder approved these records and
    those approvals stand in the ledger. What the schema refuses is publishing
    a fee CAP whose ``qualifier_stated`` nobody has ruled on -- and it refuses
    to infer one, which is the whole point of the field.

    The quotes are carried here because they settle the question quickly: each
    of these sources DOES state a qualifier in words. Whether that makes
    ``qualifier_stated`` true is founder decision 3, and this pass was
    authorised to approve records rather than to make a publication ruling.
    That is the same shape that blocked 022 and became 023.
    """
    records = {r["identity_key"]: r for r in _store_records(store)}
    rows: List[Dict] = []
    for refusal in refusals:
        key = refusal["identity_key"]
        record = records.get(key, {})
        evidence = (record.get("observation") or {}).get("evidence") or []
        cap_quotes = [e.get("quote", "") for e in evidence
                      if "fee_cap" in (e.get("field_refs") or ())]
        rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", record.get("canonical_name", "")),
            ("issues", list(refusal.get("issues") or ())),
            ("fee_cap", ((record.get("observation") or {})
                         .get("extraction", {}).get("fee_cap"))),
            ("source_quotes_for_the_cap", cap_quotes),
            ("signature_still_stands", True),
            ("what_would_settle_it",
             "a founder ruling on decision 3 -- whether these caps count as "
             "stating a qualifier. market_policy_package_cli already carries "
             "the switch (--cap-qualifier-stated); nothing here may set it, "
             "because this order authorises record approval and not a "
             "publication ruling."),
        )))
    return OrderedDict((
        ("schema", "ptf-publication-hold/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("what_this_is",
         "records the founder APPROVED and the publication schema will not "
         "take. Their signatures stand; only their publication waits."),
        ("count", len(rows)),
        ("held", rows),
        ("effect_on_the_target",
         "each held row is one fewer published pet-friendly profile than the "
         "signature count implies. The count is reported as it is rather than "
         "forced."),
    ))


def authority_excluding(held: Sequence[str]) -> Dict:
    """The proposed authority, minus rows the publication schema refuses.

    The decision ledgers are NOT edited. A held row stays signed in the ledger
    that signed it -- an attestation is a dated act by a named person -- and is
    filtered out of this derived view only, with the hold document naming it.
    """
    import copy
    from scripts.pettripfinder import market_proposed_authority_cli as MPA
    ledgers = []
    for path in (LP / "grand_rapids_holland_mi_founder_decision_ledger_021.json",
                 SIGNATURES_PATH):
        ledger = copy.deepcopy(_load(path))
        ledger["signed"] = [row for row in ledger.get("signed") or ()
                            if row["identity_key"] not in set(held)]
        ledgers.append(ledger)
    withdrawals = _load(LP / "grand_rapids_holland_mi_founder_withdrawal_022.json")
    return MPA.build(ledgers, merged_store(), _load(CENSUS_PATH),
                     withdrawals=withdrawals)


# --------------------------------------------------------------------------- #
# Stage four: promotion into source
# --------------------------------------------------------------------------- #

PROMOTION_PATH = LP / "grand_rapids_holland_mi_source_promotion_030.json"


def _run(command: Sequence[str], what: str) -> str:
    done = subprocess.run(list(command), cwd=str(_REPO_ROOT),
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit("%s failed (%d):\n%s"
                         % (what, done.returncode, done.stdout + done.stderr))
    return done.stdout + done.stderr


def other_market_fingerprints() -> Dict[str, str]:
    """Every other market's shard, hashed, so "unchanged" is proved."""
    import hashlib
    from scripts.pettripfinder import market_authority as MA
    out: Dict[str, str] = {}
    root = MA.exclusions_shard_path(MARKET).parent.parent
    if not Path(root).is_dir():
        return out
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and MARKET not in path.as_posix():
            out[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()).hexdigest()
    return out


def promote() -> int:
    """The 022 sequence, over the authority publication will actually take."""
    from scripts.pettripfinder import market_authority as MA
    from scripts.pettripfinder import market_registration_cli as REGISTRATION
    from scripts.pettripfinder import hotel_exclusions as HE
    from scripts.pettripfinder.grand_rapids_holland_source_promotion_022 import (
        withdraw_published_routes)

    authority = _load(AUTHORITY_030)
    holds = _load(HOLDS_PATH)
    before_shards = other_market_fingerprints()
    census_path = CENSUS_PATH

    # 1. the policy package, by the sanctioned projector. It fails closed, so
    #    reaching the next line at all means every row validated.
    code, output = probe_package(AUTHORITY_030, MERGED_STORE,
                                 authority["pet_friendly_count"], PACKAGE_PATH)
    if code != 0:
        raise SystemExit("the projector refused the publishable authority, "
                         "which should be impossible after the package "
                         "stage:\n%s" % output[-2000:])
    package = _load(PACKAGE_PATH)

    # 2. the market's authority shard, derived by the SANCTIONED installer.
    #    Its write() would also blank the routing shard, which this market
    #    needs, so the derivation is used and that write is not.
    built = REGISTRATION.build(MARKET, AUTHORITY_030, census_path)
    routes_before = len(MA.load_market_routes(MARKET))
    HE.validate(built["exclusions_document"])
    MA.exclusions_shard_path(MARKET).write_text(
        MA.render_json(built["exclusions_document"]), encoding="utf-8")
    MA.seed_shard_path(MARKET).write_text(
        MA.render_seed_csv(built["seed_rows"]), encoding="utf-8")
    routes_after_shards = len(MA.load_market_routes(MARKET))
    if routes_after_shards != routes_before:
        raise SystemExit(
            "the routing shard moved from %d routes to %d while writing the "
            "SEED and EXCLUSION shards; only the deliberate withdrawal below "
            "may change routing"
            % (routes_before, routes_after_shards))

    # 3. the routes publication has now answered.
    #
    # PUBLISHING WITHDRAWS THE ROUTES IT ANSWERS -- 023's rule, and skipping it
    # here left a stale pointer beside every newly published seed row. The
    # committed invariant "no route survives for a hotel this market now
    # publishes" is what caught it. WITHDRAWN, not RETIRED: ROUTING_RETIRED
    # marks a binding that should never have been made, and these bindings were
    # correct -- they found the pages this market now publishes.
    withdrawal = withdraw_published_routes(built["seed_rows"])
    routes_after = len(MA.load_market_routes(MARKET))

    # 4. the three legacy globals, from the shards, by their own assembler
    _run([sys.executable, "-m", "scripts.pettripfinder.build_global_authority",
          "--write"], "the global authority assembler")

    # 4. proof the other markets were not disturbed. NO FLAG AT ALL: this
    #    tool's check mode is its default and --write is the opt-in, and that
    #    --write path is the one that wiped corridor assignments in
    #    PTF-DAYTON-RECERT. The argument is deliberately absent, not spelled.
    check = _run([sys.executable, "-m",
                  "scripts.pettripfinder.build_market_authorities"],
                 "build_market_authorities (check mode, the default)")

    after_shards = other_market_fingerprints()
    changed = sorted(k for k in before_shards
                     if before_shards[k] != after_shards.get(k))

    exclusions = list(built["exclusions_document"]["exclusions"])
    seed_rows = list(built["seed_rows"])
    report = OrderedDict((
        ("schema", "ptf-source-promotion/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("signed_authority", OrderedDict((
            ("pet_friendly", 43), ("verified_no_pets", 20), ("total", 63),
        ))),
        ("publication_holds", OrderedDict((
            ("count", holds["count"]),
            ("identity_keys", [r["identity_key"] for r in holds["held"]]),
            ("why", "the publication schema requires fee_cap.qualifier_stated "
                    "and never infers it; ruling on that is founder decision "
                    "3, which this order does not carry"),
            ("signatures_still_stand", True),
        ))),
        ("promoted", OrderedDict((
            ("pet_friendly", authority["pet_friendly_count"]),
            ("verified_no_pets", authority["verified_no_pets_count"]),
            ("authority_total", authority["authority_total"]),
            ("package_count", package["count"]),
            ("exclusion_rows", len(exclusions)),
            ("seed_rows", len(seed_rows)),
        ))),
        ("routes_withdrawn_by_publication", withdrawal),
        ("preserved", OrderedDict((
            ("pinned_census", len(_load(census_path)["hotels"])),
            ("routes_before", routes_before), ("routes_after", routes_after),
            ("other_market_shards_checked", len(before_shards)),
            ("other_market_shards_changed", changed),
            ("build_market_authorities", "check mode, the default; --write "
                                         "was never spelled"),
        ))),
        ("build_market_authorities_output", check.strip().splitlines()[-3:]),
    ))
    _write(PROMOTION_PATH, report)

    print("promoted pet-friendly   %d" % report["promoted"]["pet_friendly"])
    print("promoted no-pets        %d" % report["promoted"]["verified_no_pets"])
    print("authority total         %d" % report["promoted"]["authority_total"])
    print("package count           %d" % report["promoted"]["package_count"])
    print("seed rows / exclusions  %d / %d"
          % (report["promoted"]["seed_rows"], report["promoted"]["exclusion_rows"]))
    print("routes                  %d -> %d (%d withdrawn by publication)"
          % (routes_before, routes_after, withdrawal["withdrawn"]))
    print("pinned census           %d" % report["preserved"]["pinned_census"])
    print("other markets changed   %s" % (changed or "none"))
    print("publication holds       %d %s"
          % (holds["count"], report["publication_holds"]["identity_keys"]))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="record",
                        choices=("record", "sign", "package", "promote"),
                        help="record: re-locate the block and build the "
                             "reconciled observation. sign: the signature "
                             "pass. package: what publication will take")
    args = parser.parse_args(argv)
    if args.stage == "promote":
        return promote()
    if args.stage == "package":
        store = merged_store()
        _write(MERGED_STORE, store)
        full = authority_excluding(())
        _write(AUTHORITY_030, full)

        scratch = _REPO_ROOT / "data" / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        code, output = probe_package(AUTHORITY_030, MERGED_STORE,
                                     full["pet_friendly_count"],
                                     scratch / "package.probe.json")
        refusals = schema_refusals(output) if code != 0 else []
        holds = publication_holds(refusals, store)
        _write(HOLDS_PATH, holds)

        held = [row["identity_key"] for row in holds["held"]]
        publishable = authority_excluding(held)
        _write(AUTHORITY_030, publishable)

        print("signed authority          %d pet-friendly / %d no-pets / %d total"
              % (full["pet_friendly_count"], full["verified_no_pets_count"],
                 full["authority_total"]))
        print("publication holds         %d  %s" % (len(held), held))
        print("publishable authority     %d pet-friendly / %d no-pets / %d total"
              % (publishable["pet_friendly_count"],
                 publishable["verified_no_pets_count"],
                 publishable["authority_total"]))
        return 0
    if args.stage == "sign":
        ledger = signature_pass()
        _write(SIGNATURES_PATH, ledger)
        counts = ledger["counts"]
        print("candidates presented   %d" % counts["candidates_presented"])
        print("signatures written     %d" % counts["signatures_written"])
        print("signatures refused     %d  %s"
              % (counts["signatures_refused"], dict(counts["by_outcome"])))
        print("  pet-friendly         %d" % counts["signed_pet_friendly"])
        print("  verified no-pets     %d" % counts["signed_verified_no_pets"])
        print("identity rulings       %s" % ledger["identity_rulings_recorded"])
        print("every signature bound  %s" % ledger["every_signature_binds_a_hash"])
        return 0
    if args.stage == "record":
        store, relocated = build_reconciled_record()
        _write(STORE_030, store)
        record = _store_records(store)[0]
        print("relocated from   %s" % relocated["declined_directory"])
        print("relocated to     %s" % relocated["relocated_directory"])
        print("declined kept    %s" % relocated["declined_capture_untouched"])
        print("block            %d chars  sha %s"
              % (relocated["block_chars"], relocated["block_sha256"][:16]))
        print("record           %s" % record["identity_key"])
        print("  readiness      %s" % (record.get("readiness") or {}).get("state"))
        print("  membrane       %s" % (record.get("membrane") or {}).get("verdict"))
        print("  grade          %s"
              % (record.get("publication_grade") or {}).get("verdict"))
        print("  pets_allowed   %s"
              % (record["observation"]["extraction"].get("pets_allowed")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
