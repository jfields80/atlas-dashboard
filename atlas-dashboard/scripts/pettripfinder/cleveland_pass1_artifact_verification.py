"""PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 Pass 1 -- artifact verification.

Closes the publication-grade evidence debt on Cleveland's 21 published policy
records WITHOUT recapturing anything: the browser captures behind them already
exist in the gitignored worker tree, recorded by hash at integration time. This
module re-derives every one of those hashes from the artifact bytes on disk,
verifies the identity the capture actually read, re-asserts every published
quote is contiguous in the captured page text, and only then upgrades the
evidence entries to the canonical publication-grade shape of
``contracts/evidence.py``.

What it deliberately does NOT do:

* It never copies an artifact into git. Captured brand pages embed real
  third-party credentials (ARTIFACT_BACKUP_RUNBOOK.md section 1); the committed
  output is hashes, paths, sizes and verdicts only.
* It never re-signs a human approval. Adding artifact bindings changes the
  record, so record_hash moves, so the operator approval that bound the old
  hash no longer describes this record. Per the PTF-POLICY-SCHEMA-MIGRATION-001A
  rule, the approval is downgraded to MACHINE_REVIEWED_PENDING_OPERATOR with the
  prior approval preserved verbatim under ``supersedes`` -- reported invalid,
  never silently rebound. The evidence SET is untouched (refs derive from
  field+quote+url), so evidence_hash is asserted unchanged.
* It never promotes an entry whose artifact bytes cannot be re-verified. The
  two Drury records' raw fetches retained page TEXT but not the HTML bytes their
  recorded html_sha256 describes, and extracted text is not one of
  ``ARTIFACT_KINDS`` -- so they are classified, reported, and left at
  POINTER_TO_EVIDENCE.

Run:
  python -m scripts.pettripfinder.cleveland_pass1_artifact_verification \
      [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-LIGHT-RECERTIFICATION-001"
PASS_DATE = "2026-08-15"
#: The agent that ran the verification. Named in the downgraded approval block
#: so nobody mistakes a mechanical hash verification for a founder review.
AGENT_IDENTITY = "claude-fable-5 (%s, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
REPORT_PATH = LP / "cleveland_artifact_verification_001.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

#: Worker-tree locations, relative to --data-root. Both are gitignored; this
#: module READS them and never writes into them.
FACTORY_BATCH = Path("worker_runs/pettripfinder/discovery/review_batches/cleveland-factory-001")
FACTORY_MANIFEST = FACTORY_BATCH / "evidence_manifest.json"
FACTORY_PROPOSAL = FACTORY_BATCH / "proposed_cleveland_authority.json"
CAPTURE_003_RAW = Path("worker_runs/pettripfinder/cleveland-policy-capture-003/raw")

#: Classification vocabulary, exactly as the work order names it.
VERIFIED_COMPLETE = "ARTIFACT_VERIFIED_COMPLETE"
VERIFIED_NO_SCREENSHOT = "ARTIFACT_VERIFIED_NO_SCREENSHOT"
PARTIAL = "ARTIFACT_PARTIAL"
MISSING = "ARTIFACT_MISSING"
HASH_MISMATCH = "ARTIFACT_HASH_MISMATCH"
IDENTITY_FAILURE = "IDENTITY_BINDING_FAILURE"

#: Only these classes may upgrade entries; PARTIAL keeps its pointers.
UPGRADEABLE = frozenset({VERIFIED_COMPLETE, VERIFIED_NO_SCREENSHOT})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bare(sha: str) -> str:
    """Hash comparison is on the hex digest; storage keeps the sha256: prefix."""
    return sha[7:] if sha.startswith("sha256:") else sha


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _collapse(value: str) -> str:
    return " ".join((value or "").split())


def _street_number(address: str) -> str:
    head = (address or "").strip().split(" ", 1)[0]
    return head if head.isdigit() else ""


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Per-record verification.
# --------------------------------------------------------------------------- #

class Verification:
    """Everything the report records about one published record."""

    def __init__(self, identity_key: str, name: str):
        self.identity_key = identity_key
        self.name = name
        self.classification = MISSING
        self.checks: "OrderedDict[str, bool]" = OrderedDict()
        self.notes: List[str] = []
        self.artifact_paths: Dict[str, str] = {}
        self.recomputed: Dict[str, str] = {}
        self.captured_at = ""
        self.capture_method = ""
        self.html_sha256 = ""
        self.quote_failures: List[str] = []
        self.entries_upgraded = 0
        self.entries_pointer = 0
        self.approval_action = "UNCHANGED"

    def check(self, label: str, ok: bool, note: str = "") -> bool:
        self.checks[label] = bool(ok)
        if not ok and note:
            self.notes.append(note)
        return bool(ok)

    def as_report_row(self) -> Dict:
        return OrderedDict([
            ("identity_key", self.identity_key),
            ("name", self.name),
            ("classification", self.classification),
            ("captured_at", self.captured_at),
            ("capture_method", self.capture_method),
            ("artifact_paths", self.artifact_paths),
            ("recomputed_sha256", self.recomputed),
            ("checks", self.checks),
            ("quote_contiguity_failures", self.quote_failures),
            ("entries_upgraded", self.entries_upgraded),
            ("entries_still_pointer", self.entries_pointer),
            ("approval_action", self.approval_action),
            ("notes", self.notes),
        ])


def _name_tokens(value: str) -> frozenset:
    return frozenset("".join(ch if ch.isalnum() else " " for ch in
                             (value or "").lower()).split())


def _identity_binding(out: Verification, census_row: Dict,
                      captured: Dict) -> bool:
    """The capture must have READ this property's identity off the page.

    The standard is the capture gate's own: independent key groups read from
    the rendered page's own JSON-LD. The street key (street number + 5-digit
    ZIP) must agree, corroborated by phone digits or by the property name.
    A page whose street key disagrees, or that matches on nothing but the
    street, binds to some OTHER property and fails.

    A phone disagreement over an agreeing street key and name is recorded as
    a note, not a failure: the page's own JSON-LD is the property speaking,
    and the census number came from a third-party directory -- a discrepancy
    to review in the census, never evidence the capture read the wrong page.
    """
    phone_census = _digits(census_row.get("phone", ""))
    phone_page = _digits(captured.get("phone", ""))
    postal_census = _digits(census_row.get("postal_code", ""))[:5]
    postal_page = _digits(captured.get("postal_code", ""))[:5]
    street_census = _street_number(census_row.get("address", ""))
    street_page = _street_number(captured.get("street", ""))
    census_name = _name_tokens(census_row.get("canonical_name", ""))
    page_name = _name_tokens(captured.get("name", ""))

    phone_ok = bool(phone_census) and bool(phone_page) and \
        phone_page.endswith(phone_census[-10:])
    street_ok = bool(postal_page) and postal_page == postal_census and \
        bool(street_page) and street_page == street_census
    name_ok = bool(census_name) and bool(page_name) and \
        (census_name <= page_name or page_name <= census_name)

    out.check("identity_street_key_agrees", street_ok,
              "page %s/%s vs census %s/%s"
              % (street_page, postal_page, street_census, postal_census))
    out.check("identity_phone_agrees", phone_ok)
    out.check("identity_name_agrees", name_ok,
              "page name %r vs census %r"
              % (captured.get("name"), census_row.get("canonical_name")))
    if street_ok and name_ok and not phone_ok:
        out.notes.append(
            "census phone %s disagrees with the page's own JSON-LD %s; "
            "street key and name bind the capture to this property -- review "
            "the census number, do not touch it in this pass"
            % (phone_census or "(absent)", phone_page or "(absent)"))
    return street_ok and (phone_ok or name_ok)


def _verify_quotes(out: Verification, hotel: Dict, page_text: str) -> None:
    """Every published quote must be contiguous in the captured page text."""
    for entry in hotel.get("evidence", []):
        quote = entry.get("quote") or ""
        if not evidence_contract.quote_is_contiguous(quote, page_text):
            out.quote_failures.append(
                "%s: %r" % (entry.get("field"), quote[:80]))
    out.check("quotes_contiguous_in_capture_text", not out.quote_failures)


def verify_factory_record(hotel: Dict, census_row: Dict, proposal_row: Dict,
                          manifest_row: Optional[Dict],
                          data_root: Path) -> Tuple[Verification, Optional[Dict]]:
    """One cleveland-factory-001 record against its on-disk capture."""
    out = Verification(hotel["identity_key"], hotel["name"])
    if manifest_row is None:
        out.classification = MISSING
        out.notes.append("no evidence_manifest entry for this hotel_id")
        return out, None

    capture_rel = manifest_row["capture_json"]["path"].replace("\\", "/")
    png_rel = manifest_row["screenshot_png"]["path"].replace("\\", "/")
    # Manifest paths are recorded relative to the repository package root.
    capture_path = data_root.parent / capture_rel
    png_path = data_root.parent / png_rel
    out.artifact_paths = {"capture_json": capture_rel, "screenshot_png": png_rel}

    if not capture_path.is_file():
        out.classification = MISSING
        out.notes.append("capture_json absent on disk")
        return out, None

    capture_file_sha = _sha256_file(capture_path)
    out.recomputed["capture_json_file"] = capture_file_sha
    file_ok = out.check(
        "capture_json_file_hash_agrees",
        capture_file_sha == manifest_row["capture_json"]["sha256"],
        "capture_json file hash moved since the manifest recorded it")

    capture = load_json(capture_path)
    html_sha = _sha256_text(capture.get("html") or "")
    text_sha = _sha256_text(capture.get("text") or "")
    out.recomputed["html_content"] = html_sha
    out.recomputed["text_content"] = text_sha
    html_ok = out.check(
        "html_sha256_agrees",
        html_sha == _bare(proposal_row["html_sha256"])
        and html_sha == capture.get("html_sha256")
        and html_sha == _bare(hotel.get("worker_result_hash", "")),
        "recomputed html hash disagrees with journal/proposal/authority")
    text_ok = out.check(
        "text_sha256_agrees",
        text_sha == _bare(proposal_row["text_sha256"])
        and text_sha == capture.get("text_sha256"),
        "recomputed text hash disagrees with journal/proposal")

    png_ok = False
    if png_path.is_file():
        png_sha = _sha256_file(png_path)
        out.recomputed["screenshot_png_file"] = png_sha
        png_ok = out.check(
            "png_sha256_agrees",
            png_sha == manifest_row["screenshot_png"]["sha256"]
            and png_sha == _bare(proposal_row["png_sha256"]),
            "screenshot hash disagrees with manifest/proposal")
    else:
        out.check("png_sha256_agrees", False, "screenshot absent on disk")

    identity = ((capture.get("automation") or {}).get("hydration") or {}) \
        .get("identity") or {}
    identity_ok = _identity_binding(out, census_row, identity)
    _verify_quotes(out, hotel, capture.get("text") or "")
    quotes_ok = not out.quote_failures

    out.captured_at = capture.get("captured_at") or proposal_row.get("captured_at", "")
    out.capture_method = "browser_assisted"
    out.html_sha256 = html_sha

    if not (file_ok and html_ok and text_ok):
        out.classification = HASH_MISMATCH
    elif not identity_ok:
        out.classification = IDENTITY_FAILURE
    elif not quotes_ok:
        out.classification = PARTIAL
    elif png_ok:
        out.classification = VERIFIED_COMPLETE
    else:
        out.classification = VERIFIED_NO_SCREENSHOT
    return out, capture


def verify_drury_record(hotel: Dict, census_row: Dict,
                        raw_path: Path) -> Verification:
    """One capture-003 deterministic fetch: text retained, html bytes not.

    The recorded html_sha256 was computed from response bytes the fetch did not
    keep, and extracted text is not an ``ARTIFACT_KINDS`` member. So the best
    honest outcome here is PARTIAL: the text artifact and every quote verify,
    and the record still needs a real page artifact before publication grade.
    """
    out = Verification(hotel["identity_key"], hotel["name"])
    out.artifact_paths = {"raw_fetch_json": str(
        raw_path.relative_to(raw_path.parents[4])).replace("\\", "/")}
    if not raw_path.is_file():
        out.classification = MISSING
        out.notes.append("capture-003 raw fetch record absent on disk")
        return out

    raw = load_json(raw_path)
    text_sha = _sha256_text(raw.get("text") or "")
    out.recomputed["text_content"] = text_sha
    text_ok = out.check("text_sha256_agrees", text_sha == raw.get("text_sha256"),
                        "recomputed text hash disagrees with the fetch record")
    out.check("html_bytes_on_disk", False,
              "html_sha256 %s was recorded from bytes the deterministic fetch "
              "did not retain; it cannot be re-verified" % raw.get("html_sha256"))
    html_matches_authority = out.check(
        "recorded_html_sha_matches_authority",
        "sha256:%s" % raw.get("html_sha256") == hotel.get("worker_result_hash"),
        "authority worker_result_hash disagrees with the fetch record")

    # Identity: capture-003 was a static fetch with no hydration identity
    # block; the binding evidence is the property-specific final URL it
    # verified plus the phone/postal expectations recorded at fetch time.
    out.check("final_url_is_property_page",
              (raw.get("final_url") or "").startswith(
                  "https://www.druryhotels.com/locations/"),
              "final URL is not a Drury property page")
    out.check("fetch_expected_identity_recorded",
              _digits(raw.get("expected_phone", "")) == _digits(census_row.get("phone", ""))
              and (raw.get("expected_postal_code") or "") == (census_row.get("postal_code") or ""),
              "fetch-time identity expectations disagree with the census")

    _verify_quotes(out, hotel, raw.get("text") or "")
    out.captured_at = "2026-08-11"
    out.capture_method = "deterministic_fetch"

    if not (text_ok and html_matches_authority):
        out.classification = HASH_MISMATCH
    else:
        out.classification = PARTIAL
    return out


# --------------------------------------------------------------------------- #
# Upgrade + approval consequence.
# --------------------------------------------------------------------------- #

def upgrade_entries(hotel: Dict, verification: Verification) -> int:
    """Bind every verified entry to the page artifact it was read from.

    Quotes, values, URLs, fields and evidence_refs are untouched -- asserted,
    not assumed: the refs are recomputed afterwards and must be identical,
    which also proves evidence_hash cannot have moved.
    """
    before_refs = sorted(e["evidence_ref"] for e in hotel["evidence"])
    upgraded = 0
    for entry in hotel["evidence"]:
        if verification.quote_failures:
            break
        entry["artifact_class"] = enums.PUBLICATION_GRADE_EVIDENCE
        entry["artifact_sha256"] = "sha256:%s" % verification.html_sha256
        entry["artifact_kind"] = enums.ARTIFACT_RENDERED_HTML
        entry["captured_at"] = verification.captured_at
        entry["capture_method"] = verification.capture_method
        entry["source_grade"] = enums.GRADE_PT1_FIRST_PARTY
        upgraded += 1
    after_refs = sorted(evidence_ref_for(e) for e in hotel["evidence"])
    if before_refs != after_refs:
        raise AssertionError(
            "%s: evidence refs moved during upgrade; upgrade must not touch "
            "quote/field/url" % hotel["identity_key"])
    return upgraded


def downgrade_approval(hotel: Dict) -> None:
    """The honest approval state for a record that changed after signature.

    Mirrors PTF-POLICY-SCHEMA-MIGRATION-001A: the prior approval is preserved
    verbatim as provenance, the state becomes machine-reviewed-pending-operator,
    and the hashes recorded are the CURRENT record's, so a later founder
    attestation has an exact target. No operator name is reused.
    """
    prior = hotel.get("approval") or {}
    signed = {k: v for k, v in hotel.items() if k != "approval"}
    new_record_hash = record_hash(signed)
    new_evidence_hash = evidence_hash(hotel.get("evidence", []))
    if prior.get("evidence_hash") != new_evidence_hash:
        raise AssertionError(
            "%s: evidence_hash moved (%s -> %s); Pass 1 must not change the "
            "evidence set" % (hotel["identity_key"],
                              str(prior.get("evidence_hash"))[7:23],
                              new_evidence_hash[7:23]))
    hotel["approval"] = OrderedDict([
        ("decision", enums.MACHINE_REVIEWED_PENDING_OPERATOR),
        ("operator", AGENT_IDENTITY),
        ("approval_date", PASS_DATE),
        ("supersedes", copy.deepcopy(dict(prior))),
        ("caveats", [
            "%s Pass 1. Entry-level artifact bindings (artifact_sha256, "
            "artifact_kind, captured_at, capture_method, source_grade) were "
            "added after every recorded capture hash was re-derived from the "
            "worker-tree artifact bytes and every published quote was "
            "re-asserted contiguous in the captured page text. Facts, quotes, "
            "source URLs and the evidence set are unchanged (evidence_hash "
            "identical); record_hash moved because the record now carries the "
            "bindings. The approval under 'supersedes' was given for the "
            "record before those bindings and is preserved verbatim; it no "
            "longer binds this record. Founder re-attestation against the "
            "record_hash below is required." % WORK_ORDER,
        ]),
        ("record_hash", new_record_hash),
        ("evidence_hash", new_evidence_hash),
    ])


# --------------------------------------------------------------------------- #
# Run.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    facts = load_json(FACTS_PATH)
    census = {row["identity_key"]: row
              for row in load_json(CENSUS_PATH)["hotels"]}
    proposal = load_json(data_root / FACTORY_PROPOSAL)
    manifest = load_json(data_root / FACTORY_MANIFEST)
    proposal_by_key = {row["listing_key"]: row
                       for row in proposal["captured_pet_friendly"]}
    manifest_by_id = {row["hotel_id"]: row for row in manifest["artifacts"]}

    drury_raw = {
        "drury inn and suites beachwood":
            data_root / CAPTURE_003_RAW / "15-drury-inn-and-suites-beachwood.json",
        "drury plaza hotel":
            data_root / CAPTURE_003_RAW / "10-drury-plaza-hotel.json",
    }

    rows: List[Verification] = []
    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        census_row = census[key]
        if key in drury_raw:
            verification = verify_drury_record(hotel, census_row, drury_raw[key])
        else:
            proposal_row = proposal_by_key[key]
            manifest_row = manifest_by_id.get(proposal_row["hotel_id"])
            verification, _ = verify_factory_record(
                hotel, census_row, proposal_row, manifest_row, data_root)

        if verification.classification in UPGRADEABLE:
            verification.entries_upgraded = upgrade_entries(hotel, verification)
            issues = evidence_contract.validate(hotel)
            if issues:
                raise AssertionError("%s: upgraded record fails the evidence "
                                     "contract: %s" % (key, issues))
            downgrade_approval(hotel)
            verification.approval_action = (
                "SUPERSEDED_PENDING_REATTESTATION_RECORD_HASH_MOVED")
        else:
            verification.entries_pointer = len(hotel.get("evidence", []))
        rows.append(verification)

    counts: Dict[str, int] = {}
    for row in rows:
        counts[row.classification] = counts.get(row.classification, 0) + 1

    report = OrderedDict([
        ("schema", "ptf-cleveland-artifact-verification/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("verified_by", AGENT_IDENTITY),
        ("rule", "An entry is promoted to PUBLICATION_GRADE_EVIDENCE only "
                 "when the artifact bytes on disk re-hash to the values "
                 "recorded at integration, the capture read this property's "
                 "own identity off the page, and the published quote is "
                 "contiguous in the captured text. Anything less keeps its "
                 "POINTER_TO_EVIDENCE class and says so here. No approval is "
                 "re-signed: a record that gained bindings after signature is "
                 "downgraded to pending-operator with the prior approval "
                 "preserved verbatim."),
        ("artifact_custody",
         "Artifact bytes remain in the gitignored worker tree and its "
         "verified snapshots (ARTIFACT_BACKUP_RUNBOOK.md); captured brand "
         "pages embed third-party credentials and are never committed. This "
         "report carries hashes, paths, sizes and verdicts only."),
        ("records_checked", len(rows)),
        ("classification_counts", counts),
        ("entries_upgraded", sum(r.entries_upgraded for r in rows)),
        ("entries_still_pointer", sum(r.entries_pointer for r in rows)),
        ("records", [row.as_report_row() for row in rows]),
    ])

    if apply:
        # LF bytes, exactly as the repo stores them: the release contract pins
        # the sha256 of the file's BYTES, and platform newline translation
        # would make that pin lie on Windows.
        payload = (json.dumps(facts, indent=2, ensure_ascii=False) + "\n") \
            .encode("utf-8")
        FACTS_PATH.write_bytes(payload)
        new_sha = hashlib.sha256(payload).hexdigest()
        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        CONTRACT_PATH.write_bytes(
            (json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        report["facts_sha256_after_apply"] = new_sha
        REPORT_PATH.write_bytes(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=_REPO_ROOT / "data",
                        help="worker-tree root (gitignored data/ directory)")
    parser.add_argument("--apply", action="store_true",
                        help="write the upgraded facts, release contract sha "
                             "and verification report")
    args = parser.parse_args()

    report = run(args.data_root, args.apply)
    print("records checked        : %d" % report["records_checked"])
    for name, count in sorted(report["classification_counts"].items()):
        print("  %-34s %d" % (name, count))
    print("evidence entries upgraded      : %d" % report["entries_upgraded"])
    print("evidence entries still pointer : %d" % report["entries_still_pointer"])
    for row in report["records"]:
        print("  %-46s %s" % (row["name"][:46], row["classification"]))
        for note in row["notes"]:
            print("      note: %s" % note)
    if not args.apply:
        print("dry run: nothing written (pass --apply to commit the upgrade)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
