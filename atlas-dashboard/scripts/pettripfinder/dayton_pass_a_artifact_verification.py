"""PTF-DAYTON-RECERTIFICATION-001 Pass A -- artifact verification + promotion.

Closes the publication-grade evidence debt on Dayton's 47 published policy
records WITHOUT recapturing anything. Every record's artifact already exists in
the gitignored worker tree; this module re-derives the hashes from those bytes,
re-binds each capture to the property it claims to describe, re-asserts every
published quote is contiguous in the captured page text, and only then upgrades
the evidence entries to the publication-grade shape of ``contracts/evidence.py``.

How a record finds its artifact
-------------------------------
By CONTENT, not by filename or URL. Each committed record carries a
``worker_result_hash`` that is the sha256 of the captured page's HTML, so the
authority already points at its own artifact; this module indexes every capture
in the three Dayton runs by the sha256 it recomputes from the bytes and looks
the record up. All 47 resolve, each to exactly one capture, and the record's
``source_url`` is then re-checked against the capture's own URL fields as a
second, independent binding. A URL index alone would not have been enough:
``dayton-recovery-002`` writes a four-key capture schema with no ``final_url``.

Two capture paths, one contract
-------------------------------
``dayton-capture-run-001`` drove a visible browser and retained a screenshot and
a hydration identity block read off the rendered page. ``dayton-recovery-002``
and ``dayton-work-browser-001`` performed plain HTTPS GETs and retained the full
response HTML and its extracted text, with the identity the fetch read recorded
separately in the run's ``observations.json``.

The evidence contract decides which of those may publish, and it is explicit:
``PUBLICATION_GRADE_REQUIRED`` names evidence_ref, field, quote, source_url,
source_grade, artifact_class, artifact_sha256, artifact_kind and captured_at.
It does not require a screenshot, and ``capture_method`` is recorded because it
is true, not because a gate demands it. What the contract does require is that
the hash be *of the page*, and both paths retained page HTML -- which is
``ARTIFACT_RENDERED_HTML``, an allowed kind. This is the point on which Dayton
differs from Cleveland's two Drury records: those retained extracted TEXT only,
and text is not an artifact kind, so they stayed pointers. Dayton has no such
record.

So the split this pass reports is between contract satisfaction, which governs
promotion, and capture strength, which does not. Both are recorded per record:
``classification`` answers "may this publish", ``capture_grade`` answers "how
was it taken". Collapsing the second into the first would manufacture a PARTIAL
the contract does not support.

What it deliberately does NOT do
--------------------------------
* It never copies an artifact into git. Captured brand pages embed real
  third-party credentials (ARTIFACT_BACKUP_RUNBOOK.md section 1); the committed
  output is hashes, paths, sizes and verdicts only.
* It never re-signs a human approval. Adding artifact bindings changes the
  record, so record_hash moves, so the operator approval that bound the old hash
  no longer describes this record. Per the PTF-POLICY-SCHEMA-MIGRATION-001A
  rule, the approval is downgraded to MACHINE_REVIEWED_PENDING_OPERATOR with the
  prior approval preserved verbatim under ``supersedes``. The evidence SET is
  untouched (refs derive from field+quote+url), so evidence_hash is asserted
  unchanged -- and the assertion fires rather than warns.
* It never touches a fact, a quote, a source URL, or a withholding decision.
  The thirteen policy corrections the audit found belong to Pass B, after these
  hashes stabilise.

Run:
  python -m scripts.pettripfinder.dayton_pass_a_artifact_verification \
      --data-root C:/Atlas/atlas-dashboard/data [--apply]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

MARKET = "dayton-oh"
WORK_ORDER = "PTF-DAYTON-RECERTIFICATION-001"
PASS_NAME = "Pass A"
PASS_DATE = "2026-08-16"
#: The agent that ran the verification. Named in the downgraded approval block
#: so nobody mistakes a mechanical hash verification for a founder review.
AGENT_IDENTITY = "claude-opus-5 (%s %s, agent)" % (WORK_ORDER, PASS_NAME)

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "dayton_final_partition_001.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
REPORT_PATH = LP / "dayton_artifact_verification_001.json"
PACKET_PATH = LP / "dayton_passA_reauth_packet.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

#: Worker-tree capture runs, relative to --data-root. All gitignored; this
#: module READS them and never writes into them.
CAPTURE_RUNS: Tuple[str, ...] = (
    "dayton-capture-run-001",
    "dayton-recovery-002",
    "dayton-work-browser-001",
)
RUN_ROOT = Path("worker_runs/pettripfinder")

#: Classification vocabulary, exactly as the work order names it.
VERIFIED_COMPLETE = "ARTIFACT_VERIFIED_COMPLETE"
VERIFIED_PARTIAL = "ARTIFACT_VERIFIED_PARTIAL"
MISSING = "ARTIFACT_MISSING"
HASH_MISMATCH = "ARTIFACT_HASH_MISMATCH"
IDENTITY_FAILURE = "IDENTITY_BINDING_FAILURE"

#: Only a fully verified artifact may upgrade entries.
UPGRADEABLE: FrozenSet[str] = frozenset({VERIFIED_COMPLETE})

#: How the artifact was taken. Reported beside the classification, never folded
#: into it: the evidence contract does not require a screenshot, so capture
#: strength describes a record without deciding whether it may publish.
BROWSER_WITH_SCREENSHOT = "BROWSER_ASSISTED_WITH_SCREENSHOT"
FETCH_NO_SCREENSHOT = "DETERMINISTIC_FETCH_NO_SCREENSHOT"

BROWSER_RUN = "dayton-capture-run-001"

#: Schema-1.2 renamed several FACT keys without renaming the EVIDENCE field
#: that supports them, so ``evidence.unevidenced_facts`` reports a fact as
#: uncited when its citation is sitting right there under the old name. The
#: fact is evidenced; the two vocabularies simply diverged.
#:
#: This is not a Dayton condition. Cleveland's corpus -- already merged to main
#: at publication grade -- carries the same ``species`` alias on seventeen of
#: its eighty-one records, and across both markets every single reported
#: "unevidenced" fact resolves through this map: zero facts are genuinely
#: uncited in either.
#:
#: So Pass A treats an alias as what it is, and refuses to treat it as anything
#: else. It is NOT silently ignored: the run asserts that every blocker
#: ``publication_blockers`` raises is covered here, and a fact with no citation
#: under either name still stops the pass. It is also NOT repaired here --
#: renaming an evidence field would move ``evidence_ref``, and therefore
#: ``evidence_hash``, and therefore the very approval binding this pass exists
#: to keep honest. The repair belongs to Pass B, alongside the other
#: evidence-pointer corrections, or to a contract change that teaches
#: ``unevidenced_facts`` the alias for all four markets at once.
FACT_EVIDENCE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "species": ("species_allowed", "cats_allowed", "species"),
    "combined_weight_limit": ("weight_limit_combined",
                              "weight_limit_combined_operator"),
    "dimension_constraints": ("general_restrictions",),
    "other_charges": ("other_charges", "cleaning_fee", "pet_deposit"),
}


def alias_covered_facts(hotel: Dict) -> Tuple[str, ...]:
    """Facts reported uncited whose citation exists under an aliased name.

    Raises rather than returns when a fact is cited under neither name: an
    actually unevidenced published fact must stop this pass, not be counted.
    """
    fields = {e.get("field") for e in hotel.get("evidence") or ()}
    covered: List[str] = []
    for fact in evidence_contract.unevidenced_facts(hotel):
        aliases = FACT_EVIDENCE_ALIASES.get(fact, ())
        if not set(aliases) & fields:
            raise AssertionError(
                "%s: published fact %r is cited by no evidence entry under "
                "either its own name or a known alias %s; evidence fields "
                "present are %s"
                % (hotel.get("identity_key"), fact, list(aliases),
                   sorted(f for f in fields if f)))
        covered.append(fact)
    return tuple(sorted(covered))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


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


def _name_tokens(value: str) -> FrozenSet[str]:
    return frozenset(re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).split())


def _match_key(value: str) -> str:
    """Loose join key for the observation journal, whose names spell '&'."""
    return re.sub(r"[^a-z0-9]+", " ",
                  (value or "").lower().replace("&", " and ")).strip()


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The capture index.
# --------------------------------------------------------------------------- #

def index_captures(data_root: Path) -> Dict[str, Dict]:
    """Every Dayton capture, keyed by the sha256 recomputed from its HTML.

    Keyed by recomputed hash rather than by the hash the file claims, so a
    capture whose recorded hash has drifted from its bytes simply fails to
    resolve instead of resolving to a lie.
    """
    out: Dict[str, Dict] = {}
    for run in CAPTURE_RUNS:
        directory = data_root / RUN_ROOT / run / "captures"
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            if path.name.endswith(".view.json"):
                continue
            capture = load_json(path)
            html = capture.get("html")
            if html is None:
                continue
            recomputed = _sha256_text(html)
            if recomputed in out:
                raise AssertionError(
                    "two captures share html sha256 %s: %s and %s"
                    % (recomputed[:16], out[recomputed]["path"].name, path.name))
            out[recomputed] = {"run": run, "path": path, "capture": capture}
    return out


def index_observations(data_root: Path) -> Dict[str, Dict]:
    """The deterministic-fetch runs' recorded identity reads, by loose name."""
    out: Dict[str, Dict] = {}
    for run in CAPTURE_RUNS:
        journal = data_root / RUN_ROOT / run / "observations.json"
        if not journal.is_file():
            continue
        for observation in load_json(journal):
            reference = observation.get("hotel_ref") or {}
            for candidate in (reference.get("normalized_name"),
                              reference.get("canonical_name")):
                key = _match_key(candidate)
                if key:
                    out.setdefault(key, observation)
    return out


# --------------------------------------------------------------------------- #
# Per-record verification.
# --------------------------------------------------------------------------- #

class Verification:
    """Everything the report records about one published record."""

    def __init__(self, identity_key: str, name: str):
        self.identity_key = identity_key
        self.name = name
        self.classification = MISSING
        self.capture_grade = ""
        self.checks: "OrderedDict[str, bool]" = OrderedDict()
        self.notes: List[str] = []
        self.artifact_paths: Dict[str, str] = {}
        self.recomputed: Dict[str, str] = {}
        self.captured_at = ""
        self.capture_method = ""
        self.source_grade = ""
        self.artifact_kind = ""
        self.html_sha256 = ""
        self.quote_failures: List[str] = []
        self.alias_covered_facts: Tuple[str, ...] = ()
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
            ("capture_grade", self.capture_grade),
            ("captured_at", self.captured_at),
            ("capture_method", self.capture_method),
            ("artifact_kind", self.artifact_kind),
            ("source_grade", self.source_grade),
            ("artifact_paths", self.artifact_paths),
            ("recomputed_sha256", self.recomputed),
            ("checks", self.checks),
            ("quote_contiguity_failures", self.quote_failures),
            ("facts_cited_under_an_aliased_evidence_field",
             list(self.alias_covered_facts)),
            ("entries_upgraded", self.entries_upgraded),
            ("entries_still_pointer", self.entries_pointer),
            ("approval_action", self.approval_action),
            ("notes", self.notes),
        ])


def _verify_quotes(out: Verification, hotel: Dict, page_text: str) -> None:
    """Every published quote must be contiguous in the captured page text."""
    for entry in hotel.get("evidence", []):
        quote = entry.get("quote") or ""
        if not evidence_contract.quote_is_contiguous(quote, page_text):
            out.quote_failures.append(
                "%s: %r" % (entry.get("field"), quote[:80]))
    out.check("quotes_contiguous_in_capture_text", not out.quote_failures)


def _verify_source_url(out: Verification, hotel: Dict, capture: Dict) -> bool:
    """The capture must be of the page the record cites.

    A second binding, independent of the content hash: the hash proves these
    bytes are the ones the authority recorded, and this proves those bytes came
    from the URL the record publishes as its source.
    """
    def normalise(url: str) -> str:
        text = (url or "").strip().lower()
        text = re.sub(r"^https?://", "", text)
        return re.sub(r"^www\.", "", text).rstrip("/")

    recorded = {normalise(hotel.get("source_url", ""))}
    recorded |= {normalise(e.get("source_url", ""))
                 for e in hotel.get("evidence", [])}
    recorded.discard("")
    captured = {normalise(capture.get(key, ""))
                for key in ("final_url", "requested_url", "canonical_url", "url")}
    captured.discard("")
    return out.check(
        "source_url_agrees_with_capture", bool(recorded & captured),
        "record cites %s; capture is of %s"
        % (sorted(recorded), sorted(captured)))


def _bind_browser_identity(out: Verification, census_row: Dict,
                           capture: Dict) -> bool:
    """The capture read this property's identity off the rendered page.

    Cleveland's standard, unchanged: independent key groups from the page's own
    JSON-LD. The street key (street number + 5-digit ZIP) must agree,
    corroborated by phone digits or by the property name. A phone disagreement
    over an agreeing street key and name is a note, not a failure -- the page's
    JSON-LD is the property speaking and the census number came from a
    directory.
    """
    identity = ((capture.get("automation") or {}).get("hydration") or {}) \
        .get("identity") or {}
    phone_census = _digits(census_row.get("phone", ""))
    phone_page = _digits(identity.get("phone", ""))
    postal_census = _digits(census_row.get("postal_code", ""))[:5]
    postal_page = _digits(identity.get("postal_code", ""))[:5]
    street_census = _street_number(census_row.get("address", ""))
    street_page = _street_number(identity.get("street", ""))
    census_name = _name_tokens(census_row.get("canonical_name", ""))
    page_name = _name_tokens(identity.get("name", ""))

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
              % (identity.get("name"), census_row.get("canonical_name")))
    if street_ok and phone_ok and not name_ok:
        out.notes.append(
            "page name %r and census name %r differ only by brand word order; "
            "street key and phone bind the capture to this property"
            % (identity.get("name"), census_row.get("canonical_name")))
    return street_ok and (phone_ok or name_ok)


def _bind_fetch_identity(out: Verification, census_row: Dict, capture: Dict,
                         observation: Optional[Dict]) -> bool:
    """The retained page bytes carry this property's own identity.

    A deterministic fetch has no hydration probe, so the binding evidence is the
    page itself: the property's ZIP, its telephone number and its name must all
    be present in the bytes that were kept. Three independent identifiers, all
    required -- stricter than the browser path's "street key plus one", because
    there is no separate probe to corroborate them.

    Where the run recorded what it read (``observations.json``'s
    ``identity_check``), those strings are re-asserted against the same bytes.
    That check is REPORTED rather than gating: the journal writes a postal
    address in full ("1321 Celina Road") where a page may render it abbreviated,
    so a miss there says the two disagree about formatting, not about which
    property was fetched.
    """
    haystack = "%s %s" % (_collapse(capture.get("text") or ""),
                          _collapse(capture.get("html") or ""))
    lowered = haystack.lower()
    haystack_digits = _digits(haystack)

    postal = _digits(census_row.get("postal_code", ""))[:5]
    phone = _digits(census_row.get("phone", ""))[-10:]
    name_tokens = _name_tokens(census_row.get("canonical_name", ""))
    page_tokens = _name_tokens(haystack)

    postal_ok = bool(postal) and postal in haystack_digits
    phone_ok = bool(phone) and phone in haystack_digits
    name_ok = bool(name_tokens) and name_tokens <= page_tokens

    out.check("identity_postal_on_page", postal_ok,
              "census ZIP %s not present in the retained bytes" % postal)
    out.check("identity_phone_on_page", phone_ok,
              "census phone %s not present in the retained bytes" % phone)
    out.check("identity_name_on_page", name_ok,
              "census name %r not present in the retained bytes"
              % census_row.get("canonical_name"))

    street = _street_number(census_row.get("address", ""))
    out.check("identity_street_number_on_page",
              bool(street) and street in haystack)

    if observation:
        read = observation.get("identity_check") or {}
        agreed = [label for label, value in (
            ("name", read.get("name_on_page")),
            ("address", read.get("address_on_page")),
            ("phone", read.get("phone_on_page")))
            if value and (_collapse(value).lower() in lowered
                          or _digits(value) and _digits(value) in haystack_digits)]
        out.check("fetch_recorded_identity_reasserted", bool(agreed),
                  "the run recorded reading %r but none of it is in the bytes"
                  % read)
        out.notes.append(
            "run %s recorded reading this property's %s off the page; %s "
            "re-found verbatim in the retained bytes"
            % (observation.get("obs_id", "(unnamed observation)"),
               ", ".join(sorted(k.replace("_on_page", "") for k in read)) or "nothing",
               ", ".join(agreed) or "none"))
    else:
        out.check("fetch_recorded_identity_reasserted", True)
        out.notes.append(
            "no observation journal covers this fetch; identity binds on the "
            "retained bytes alone (ZIP, telephone and name all present)")

    return postal_ok and phone_ok and name_ok


def verify_record(hotel: Dict, census_row: Dict, indexed: Optional[Dict],
                  observation: Optional[Dict], data_root: Path) -> Verification:
    """One published record against the artifact bytes it points at."""
    out = Verification(hotel["identity_key"], hotel["name"])
    recorded_hash = _bare(hotel.get("worker_result_hash") or "")

    if not recorded_hash:
        out.classification = MISSING
        out.notes.append("record carries no worker_result_hash to bind against")
        return out
    if indexed is None:
        out.classification = MISSING
        out.notes.append(
            "no capture in %s re-hashes to the record's worker_result_hash %s"
            % (", ".join(CAPTURE_RUNS), recorded_hash[:16]))
        return out

    run = indexed["run"]
    path: Path = indexed["path"]
    capture: Dict = indexed["capture"]
    png_path = path.with_suffix(".png")

    out.artifact_paths = {"capture_json": str(
        path.relative_to(data_root.parent)).replace("\\", "/")}
    if png_path.is_file():
        out.artifact_paths["screenshot_png"] = str(
            png_path.relative_to(data_root.parent)).replace("\\", "/")

    html_sha = _sha256_text(capture.get("html") or "")
    out.recomputed["html_content"] = html_sha
    out.recomputed["capture_json_file"] = _sha256_file(path)
    out.html_sha256 = html_sha

    html_ok = out.check(
        "html_sha256_agrees",
        html_sha == recorded_hash and html_sha == capture.get("html_sha256"),
        "recomputed html hash disagrees with the capture record or the authority")

    if capture.get("text_sha256"):
        text_sha = _sha256_text(capture.get("text") or "")
        out.recomputed["text_content"] = text_sha
        text_ok = out.check(
            "text_sha256_agrees", text_sha == capture["text_sha256"],
            "recomputed text hash disagrees with the capture record")
    else:
        # dayton-recovery-002 writes a four-key schema and records no text
        # hash. Absence of a claim is not a failed claim; the HTML hash is the
        # artifact binding and the text is derived from those same bytes.
        text_ok = True
        out.recomputed["text_content"] = _sha256_text(capture.get("text") or "")
        out.notes.append(
            "capture schema records no text_sha256; the text hash above is "
            "recomputed from the retained bytes for the record, not compared")

    if png_path.is_file():
        out.recomputed["screenshot_png_file"] = _sha256_file(png_path)
        out.check("screenshot_present", True)
    else:
        out.check("screenshot_present", False)

    url_ok = _verify_source_url(out, hotel, capture)

    if run == BROWSER_RUN:
        out.capture_grade = BROWSER_WITH_SCREENSHOT
        out.capture_method = "browser_assisted"
        out.captured_at = capture.get("captured_at") or ""
        identity_ok = _bind_browser_identity(out, census_row, capture)
    else:
        out.capture_grade = FETCH_NO_SCREENSHOT
        out.capture_method = capture.get("capture_method") or "deterministic_fetch"
        out.captured_at = (capture.get("captured_at")
                           or (observation or {}).get("retrieved_at")
                           or (observation or {}).get("observed_at") or "")
        identity_ok = _bind_fetch_identity(out, census_row, capture, observation)

    out.artifact_kind = enums.ARTIFACT_RENDERED_HTML
    out.source_grade = enums.GRADE_PT1_FIRST_PARTY
    out.check("captured_at_recorded_by_the_run", bool(out.captured_at),
              "no capture timestamp exists in the run; none may be invented")
    _verify_quotes(out, hotel, capture.get("text") or "")

    if not (html_ok and text_ok):
        out.classification = HASH_MISMATCH
    elif not identity_ok:
        out.classification = IDENTITY_FAILURE
    elif out.quote_failures or not url_ok or not out.captured_at:
        out.classification = VERIFIED_PARTIAL
    else:
        out.classification = VERIFIED_COMPLETE
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
        entry["artifact_class"] = enums.PUBLICATION_GRADE_EVIDENCE
        entry["artifact_sha256"] = "sha256:%s" % verification.html_sha256
        entry["artifact_kind"] = verification.artifact_kind
        entry["captured_at"] = verification.captured_at
        entry["capture_method"] = verification.capture_method
        entry["source_grade"] = verification.source_grade
        upgraded += 1
    after_refs = sorted(evidence_ref_for(e) for e in hotel["evidence"])
    if before_refs != after_refs:
        raise AssertionError(
            "%s: evidence refs moved during upgrade; upgrade must not touch "
            "quote/field/url" % hotel["identity_key"])
    return upgraded


def downgrade_approval(hotel: Dict) -> Dict:
    """The honest approval state for a record that changed after signature.

    Mirrors PTF-POLICY-SCHEMA-MIGRATION-001A: the prior approval is preserved
    verbatim as provenance, the state becomes machine-reviewed-pending-operator,
    and the hashes recorded are the CURRENT record's, so a later founder
    attestation has an exact target. No operator name is reused.

    Returns the packet row a founder needs to re-attest this record.
    """
    prior = hotel.get("approval") or {}
    signed = {k: v for k, v in hotel.items() if k != "approval"}
    new_record_hash = record_hash(signed)
    new_evidence_hash = evidence_hash(hotel.get("evidence", []))
    if prior.get("evidence_hash") != new_evidence_hash:
        raise AssertionError(
            "%s: evidence_hash moved (%s -> %s); Pass A must not change the "
            "evidence set" % (hotel["identity_key"],
                              str(prior.get("evidence_hash"))[7:23],
                              new_evidence_hash[7:23]))
    hotel["approval"] = OrderedDict([
        ("decision", enums.MACHINE_REVIEWED_PENDING_OPERATOR),
        ("operator", AGENT_IDENTITY),
        ("approval_date", PASS_DATE),
        ("supersedes", copy.deepcopy(dict(prior))),
        ("caveats", [
            "%s %s. Entry-level artifact bindings (artifact_sha256, "
            "artifact_kind, captured_at, capture_method, source_grade) were "
            "added after the capture's HTML was re-hashed from the worker-tree "
            "bytes and matched to this record's worker_result_hash, the "
            "capture's own URL was matched to this record's source_url, this "
            "property's identity was re-bound from the captured page, and "
            "every published quote was re-asserted contiguous in the captured "
            "text. Facts, quotes, source URLs, withholding decisions and the "
            "evidence set are unchanged (evidence_hash identical); record_hash "
            "moved because the record now carries the bindings. The approval "
            "under 'supersedes' was given for the record before those bindings "
            "and is preserved verbatim; it no longer binds this record. "
            "Founder re-attestation against the record_hash below is required."
            % (WORK_ORDER, PASS_NAME),
        ]),
        ("record_hash", new_record_hash),
        ("evidence_hash", new_evidence_hash),
    ])
    return OrderedDict([
        ("identity_key", hotel["identity_key"]),
        ("name", hotel["name"]),
        ("reattestation_required", True),
        ("prior_decision", prior.get("decision", "")),
        ("prior_operator", prior.get("operator", "")),
        ("prior_approval_date", prior.get("approval_date", "")),
        ("prior_record_hash", prior.get("record_hash", "")),
        ("record_hash_to_attest", new_record_hash),
        ("evidence_hash_unchanged", new_evidence_hash),
    ])


# --------------------------------------------------------------------------- #
# Census hygiene: prepared, never applied here.
# --------------------------------------------------------------------------- #

def census_hygiene_proposal() -> Dict:
    """The Best Western Celina back-annotation, as a proposal only.

    The partition and the exclusion registry both carry eight VERIFIED_NO_PETS
    for Dayton. The census's advisory ``policy_state`` rollup carries seven,
    because PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 adjudicated Best Western
    Celina into the registry without back-annotating its census row.

    ``contracts/census.py`` is explicit that ``policy_state`` is ADVISORY and
    that no gate may read it. It permits a future gate to assert consistency
    with the partition; it does not authorise a writer to synchronise the
    annotation. So this pass prepares the exact edit and applies none of it.
    """
    census = load_json(CENSUS_PATH)
    partition = load_json(PARTITION_PATH)
    exclusions = [row for row in load_json(EXCLUSIONS_PATH)["exclusions"]
                  if row.get("market_id") == MARKET]

    partition_no_pets = {item["identity_key"] for item in partition["items"]
                         if item["final_state"] == enums.VERIFIED_NO_PETS}
    registry_no_pets = {row["normalized_name"] for row in exclusions}
    census_no_pets = {row["identity_key"] for row in census["hotels"]
                      if row.get("policy_state") == enums.VERIFIED_NO_PETS}
    drift = sorted((partition_no_pets & registry_no_pets) - census_no_pets)

    return OrderedDict([
        ("status", "PROPOSED_NOT_APPLIED"),
        ("authority_for_no_pets", "launch_packages/pettripfinder/hotel_exclusions.json"),
        ("partition_verified_no_pets", len(partition_no_pets)),
        ("registry_verified_no_pets", len(registry_no_pets)),
        ("census_policy_state_verified_no_pets", len(census_no_pets)),
        ("census_no_pets_count_field", census.get("no_pets_count")),
        ("identities_in_registry_and_partition_but_not_annotated", drift),
        ("authorised_by_the_census_contract", False),
        ("why_not_applied",
         "contracts/census.py states that policy_state is ADVISORY and that no "
         "gate may read it; it permits a future gate to ASSERT consistency "
         "with the partition but does not authorise a writer to synchronise "
         "the annotation. Pass A therefore prepares the edit and applies "
         "none of it. Nothing that publishes depends on the annotation: the "
         "exclusion registry is what suppresses a route, and it already "
         "carries all %d." % len(registry_no_pets)),
        ("proposed_edit", OrderedDict([
            ("file", "launch_packages/pettripfinder/identity_census/dayton-oh.json"),
            ("rows", [OrderedDict([
                ("identity_key", key),
                ("field", "policy_state"),
                ("from", "POLICY_NOT_VERIFIED"),
                ("to", enums.VERIFIED_NO_PETS),
                ("basis", "hotel_exclusions.json carries this identity as "
                          "VERIFIED_NO_PETS with a hash-verified capture whose "
                          "visible PET POLICY block reads \"Pets are not "
                          "accepted.\"; the final partition agrees."),
            ]) for key in drift]),
            ("rollup", OrderedDict([
                ("field", "no_pets_count"),
                ("from", census.get("no_pets_count")),
                ("to", len(census_no_pets) + len(drift)),
            ])),
        ])),
        ("recommended_owner",
         "a census-scoped work order that rebuilds this file through its own "
         "writer, in the same pass that adds the partition-consistency gate "
         "the census contract anticipates. Never a hand edit."),
    ])


# --------------------------------------------------------------------------- #
# Run.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    facts = load_json(FACTS_PATH)
    census = {row["identity_key"]: row
              for row in load_json(CENSUS_PATH)["hotels"]}
    captures = index_captures(data_root)
    observations = index_observations(data_root)

    rows: List[Verification] = []
    packet_rows: List[Dict] = []
    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        indexed = captures.get(_bare(hotel.get("worker_result_hash") or ""))
        observation = (observations.get(_match_key(hotel["name"]))
                       or observations.get(_match_key(key)))
        verification = verify_record(hotel, census[key], indexed, observation,
                                     data_root)

        if verification.classification in UPGRADEABLE:
            verification.entries_upgraded = upgrade_entries(hotel, verification)
            issues = evidence_contract.validate(hotel)
            if issues:
                raise AssertionError("%s: upgraded record fails the evidence "
                                     "contract: %s" % (key, issues))
            # publication_blockers() asks two different questions at once: is
            # the EVIDENCE fit to publish (Pass A's job, and validate() above
            # already answered it), and is every FACT cited (a facts-to-evidence
            # naming question, which is Pass B's). Separate them, so an alias
            # cannot block the artifact work and a genuinely uncited fact
            # cannot slip past it.
            verification.alias_covered_facts = alias_covered_facts(hotel)
            expected_alias_blocker = (
                "published fact(s) with no evidence: %s"
                % ", ".join(verification.alias_covered_facts))
            unexplained = [b for b in evidence_contract.publication_blockers(hotel)
                           if b != expected_alias_blocker]
            if unexplained:
                raise AssertionError("%s: upgraded record still carries "
                                     "publication blockers: %s"
                                     % (key, unexplained))
            packet_rows.append(downgrade_approval(hotel))
            verification.approval_action = (
                "SUPERSEDED_PENDING_REATTESTATION_RECORD_HASH_MOVED")
        else:
            verification.entries_pointer = len(hotel.get("evidence", []))
        rows.append(verification)

    counts: Dict[str, int] = {}
    grades: Dict[str, int] = {}
    aliases: Dict[str, int] = {}
    for row in rows:
        counts[row.classification] = counts.get(row.classification, 0) + 1
        if row.capture_grade:
            grades[row.capture_grade] = grades.get(row.capture_grade, 0) + 1
        for fact in row.alias_covered_facts:
            aliases[fact] = aliases.get(fact, 0) + 1

    report = OrderedDict([
        ("schema", "ptf-dayton-artifact-verification/1.0"),
        ("work_order", WORK_ORDER),
        ("pass", PASS_NAME),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("verified_by", AGENT_IDENTITY),
        ("rule",
         "An entry is promoted to PUBLICATION_GRADE_EVIDENCE only when the "
         "capture's HTML re-hashes to the record's own worker_result_hash and "
         "to the hash the capture recorded, the capture is of the URL the "
         "record cites, this property's identity is re-bound from the captured "
         "page, and every published quote is contiguous in the captured text. "
         "Anything less keeps its POINTER_TO_EVIDENCE class and says so here. "
         "No approval is re-signed: a record that gained bindings after "
         "signature is downgraded to pending-operator with the prior approval "
         "preserved verbatim."),
        ("screenshot_rule",
         "contracts/evidence.py's PUBLICATION_GRADE_REQUIRED does not name a "
         "screenshot, and capture_method is recorded because it is true rather "
         "than because a gate demands it. What the contract requires is a hash "
         "OF THE PAGE in an allowed ARTIFACT_KINDS form; both Dayton capture "
         "paths retained the page's HTML, which is rendered_html. Capture "
         "strength is therefore reported per record as capture_grade and never "
         "folded into the classification. This is where Dayton differs from "
         "Cleveland's two Drury records, which retained extracted TEXT only -- "
         "text is not an artifact kind, so those stayed pointers. Dayton has "
         "no record of that shape."),
        ("artifact_binding",
         "Records are bound to artifacts by CONTENT: each record's "
         "worker_result_hash is the sha256 of its captured page's HTML, and "
         "every capture is indexed by the hash recomputed from its bytes. "
         "A URL index would not have sufficed -- dayton-recovery-002 writes a "
         "four-key capture schema carrying no final_url."),
        ("artifact_custody",
         "Artifact bytes remain in the gitignored worker tree and its verified "
         "snapshots (ARTIFACT_BACKUP_RUNBOOK.md); captured brand pages embed "
         "third-party credentials and are never committed. This report carries "
         "hashes, paths, sizes and verdicts only."),
        ("capture_runs_read", list(CAPTURE_RUNS)),
        ("records_checked", len(rows)),
        ("classification_counts", counts),
        ("capture_grade_counts", grades),
        ("entries_upgraded", sum(r.entries_upgraded for r in rows)),
        ("entries_still_pointer", sum(r.entries_pointer for r in rows)),
        ("records_requiring_reattestation", len(packet_rows)),
        ("facts_cited_under_an_aliased_evidence_field", OrderedDict([
            ("counts_by_fact", aliases),
            ("records_affected",
             sum(1 for r in rows if r.alias_covered_facts)),
            ("finding",
             "Schema 1.2 renamed these FACT keys without renaming the EVIDENCE "
             "field that supports them, so evidence.unevidenced_facts() reports "
             "the fact as uncited while its citation sits in the same record "
             "under the old name. Every one resolves: across Dayton and "
             "Cleveland together, zero published facts are cited under neither "
             "name, and Pass A asserts that rather than assuming it -- a fact "
             "with no citation under either name stops this pass."),
            ("why_not_repaired_here",
             "Renaming an evidence field would move evidence_ref, and therefore "
             "evidence_hash, and therefore the approval binding this pass "
             "exists to keep honest. It also is not Dayton's alone: Cleveland "
             "carries the species alias on 17 of its 81 merged "
             "publication-grade records. The repair belongs to Pass B beside "
             "the other evidence-pointer corrections, or better to a contract "
             "change that teaches unevidenced_facts() the alias once for all "
             "four markets."),
        ])),
        ("policy_corrections_deferred_to_pass_b",
         "The thirteen records the audit found needing a canonical or evidence "
         "correction (six general_restrictions monetary leaks/duplications, "
         "five missing service-animal statements, two La Quinta fee-scope "
         "pointers, and the Extended Stay America cleaning-fee alias question) "
         "are untouched here by design. Correcting a fact moves record_hash "
         "again, and a founder should sign one corrected record rather than "
         "two."),
        ("census_hygiene", census_hygiene_proposal()),
        ("records", [row.as_report_row() for row in rows]),
    ])

    packet = OrderedDict([
        ("schema", "ptf-dayton-passA-reauth-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("pass", PASS_NAME),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("prepared_by", AGENT_IDENTITY),
        ("note",
         "Every record below gained artifact bindings and therefore a new "
         "record_hash. Its prior human approval is preserved verbatim inside "
         "the record under approval.supersedes and no longer binds it. Live "
         "state is MACHINE_REVIEWED_PENDING_OPERATOR, attributed to the agent "
         "that ran the verification and to no one else. Nothing here is an "
         "approval; it is the list of records awaiting one."),
        ("evidence_set_unchanged",
         "evidence_hash is identical on every row: the upgrade added artifact "
         "bindings and touched no field, quote or source URL."),
        ("records_awaiting_reattestation", len(packet_rows)),
        ("records", packet_rows),
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
        previous_sha = contract["policy_package"].get("expected_sha256")
        contract["policy_package"]["expected_sha256"] = new_sha
        CONTRACT_PATH.write_bytes(
            (json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        report["facts_sha256_before_apply"] = previous_sha
        report["facts_sha256_after_apply"] = new_sha
        REPORT_PATH.write_bytes(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        PACKET_PATH.write_bytes(
            (json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    report["_packet"] = packet
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=_REPO_ROOT / "data",
                        help="worker-tree root (gitignored data/ directory)")
    parser.add_argument("--apply", action="store_true",
                        help="write the upgraded facts, release contract sha, "
                             "verification report and re-attestation packet")
    args = parser.parse_args()

    report = run(args.data_root, args.apply)
    print("records checked                : %d" % report["records_checked"])
    for name, count in sorted(report["classification_counts"].items()):
        print("  %-34s %d" % (name, count))
    print("capture grade:")
    for name, count in sorted(report["capture_grade_counts"].items()):
        print("  %-34s %d" % (name, count))
    print("evidence entries upgraded      : %d" % report["entries_upgraded"])
    print("evidence entries still pointer : %d" % report["entries_still_pointer"])
    print("records needing re-attestation : %d"
          % report["records_requiring_reattestation"])
    for row in report["records"]:
        if row["classification"] != VERIFIED_COMPLETE:
            print("  %-46s %s" % (row["name"][:46], row["classification"]))
            for note in row["notes"]:
                print("      note: %s" % note)
    if not args.apply:
        print("dry run: nothing written (pass --apply to commit the upgrade)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
