"""PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 -- adjudicate the Dayton Work-browser pass.

The founder ran the 90-property Dayton review queue through a ChatGPT Work
browser and handed back 21 files: nine batch review CSVs, nine batch manifests,
a rolled-up review CSV, a rolled-up manifest, and a screenshot queue. This
module is the integrator's side of that handback. It re-derives every count
rather than trusting the manifests, adjudicates all 90 properties into mutually
exclusive outcomes, and writes ONE tracked ledger.

THE TRANSCRIPTION IS NOT AN ARTIFACT CLASS
------------------------------------------
For each property the package carries the operator's typed record of what the
browser displayed: a name, an address, a ZIP, and the pet wording as prose in a
spreadsheet cell. Its own manifest declares ``screenshots_created: false``, and
there is no ``screenshots/`` tree under the Dayton evidence directory at all.

Atlas requires an artifact of the surface a fact was read from, in three
separate places, each checked against this package:

  * ``hotel_policy_facts_dayton-oh.json``. Every one of the 44 committed Dayton
    records carries ``worker_result_hash``, and both integrators that ever wrote
    one (``integrate_dayton_authority``, ``integrate_dayton_recovery_002``) set
    it from a capture's ``html_sha256``.
  * ``hotel_exclusions.json``. ``source_hash`` is in ``REQUIRED_FIELDS``; a
    refusal is guarded at the same bar as a permission.
  * ``policy_membrane`` M9 -- no field without a quote -- is enforceable only
    against a stored surface. Every prior Dayton integration asserts each quote
    is a literal substring of its own capture's raw HTML before the fact it
    carries may publish.

So the transcription publishes nothing on its own word. That is the same verdict
``integrate_cleveland_work_browser_001`` reached for the 135-property Cleveland
pass, and it is reached here by consulting the contracts rather than by assuming
it.

WHAT THE TRANSCRIPTION IS GOOD FOR, AND WHAT IT UNLOCKED
--------------------------------------------------------
It is a pointer. Every transcribed quote in the package was tested against the
hash-verified captures already stored in this repository, and fourteen of the
forty-one are literal, contiguous substrings of one. Ten of those fourteen
belong to properties PTF-DAYTON-CANDIDATE-PROMOTION-001 has already published,
and one (Wingate Dayton North) is the marketing blurb that readiness holds at
POLICY_PARTIAL. The remaining three are the finding:

  ``best-western-celina``, ``best-western-plus-miamisburg-dayton`` and
  ``best-western-wapakoneta-inn`` were all recorded ACCESS_BLOCKED by
  ``dayton_recovery_002_closeout`` ("bestwestern.com 403"), because that run's
  STATIC fetch was walled. The attended ``dayton-capture-run-001`` controller
  had already captured all three successfully on 2026-08-10, and those captures
  -- hash re-derives, ``final_url`` equals the census ``_official_url`` -- carry
  the property's own PET POLICY block verbatim. The browser pass is what made
  anyone look. Nothing publishes from it; three things publish from the captures
  it pointed at.

A fourth publishes from a capture this work order made itself. Verifying the
fourteen ROUTING_CORRECTION_PROPOSED rows meant fetching the proposed URLs; two
of the fourteen answered a plain GET, and one of those two --
``extended-stay-america-select-suites-dayton-miamisburg`` -- serves the same
Pet Policy block as its three already-published Extended Stay America siblings.

BEST WESTERN'S ``petsAllowed`` IS BRAND BOILERPLATE, AND ONE MARKET ALREADY
ACTED ON IT
---------------------------------------------------------------------------
Every Best Western capture in this repository -- five distinct property pages
across Columbus and Dayton -- carries ``"petsAllowed": false`` in the JSON-LD
``Hotel`` node. Four of those five simultaneously state, in the visible PET
POLICY block on the same page, "We are Pet Friendly and allow up to two dogs
... The Pet Friendly rate is N USD per day", with N differing per property
(20, 25, 40). A field that reads ``false`` on a hotel that charges $40 a day
for a dog, and ``false`` on the one hotel that says "Pets are not accepted",
discriminates nothing. It is not evidence about any individual property, so it
is not authored as an establishing observation here, and the two affirmative
Dayton Best Westerns publish on their visible, priced, property-specific block.

This is recorded rather than merely used, because PTF-NEGATIVE-EVIDENCE-P0-001
excluded TWO COLUMBUS PROPERTIES on exactly that field:
``excl-best-western-canal-winchester-inn-columbus-south-east`` and
``excl-best-western-executive-inn`` are VERIFIED_NO_PETS whose own retained
captures say "The Pet Friendly rate is 40 USD per day" and "25.00 USD per day"
respectively. Columbus is frozen and is not this work order's to change, and no
byte of it is touched here; the finding is carried in the ledger under
``cross_market_findings`` with an exact next action.

Best Western Celina's exclusion therefore rests on its visible sentence "Pets
are not accepted." alone -- the same slot where its siblings state a rate -- and
explicitly NOT on the JSON-LD, which would have said the same thing either way.

Run:  python -m scripts.pettripfinder.integrate_dayton_work_browser_001 [--apply]
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                    # noqa: E402
from scripts.pettripfinder.identity_routing import (                        # noqa: E402
    BINDING_BRAND_INDEX,
    BINDING_PAGE_RENDERED,
    ROUTING_CONFIRMED,
    ROUTING_HELD,
    registrable_domain,
    validate_authority,
    validate_record,
)
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD          # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MB              # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO           # noqa: E402
from scripts.pettripfinder.policy import readiness as RD                    # noqa: E402
from scripts.pettripfinder.site_data import normalize_name                  # noqa: E402
from scripts.pettripfinder.contracts import enums          # noqa: E402

MARKET = "dayton-oh"
CATEGORY = "pet-friendly-hotels"
RUN_ID = "dayton-work-browser-001"
WORK_ORDER = "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001"
AS_OF = "2026-08-12"
REVIEWER = "jfields80"
SCHEMA = "ptf-dayton-work-browser-adjudication/1.0"

#: The operator package. Untracked by design -- ``data/`` is gitignored, and
#: research residue is not authority. Every consumer of this module must treat
#: its absence as a skip, never as an empty result.
INPUT_DIR = (_REPO_ROOT / "data" / "operator_evidence" / "dayton-founder-review-001"
             / "incoming" / "work-browser-pass-001")

#: Capture runs this module reads. ``dayton-capture-run-001`` is the attended
#: controller run whose artifacts the browser pass turned out to corroborate;
#: ``dayton-work-browser-001`` holds the two pages this work order fetched
#: itself while verifying routing proposals; ``dayton-recovery-002`` is read so
#: the corroboration measurement covers the whole market rather than only the
#: part that was still open -- ten of its captures already back a published
#: record, and saying so is what makes "five of forty-one are NEW" a fact
#: instead of an artefact of where this module happened to look.
CAPTURE_DIRS = (
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "dayton-capture-run-001" / "captures",
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "dayton-recovery-002" / "captures",
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID / "captures",
)

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / ("%s.json" % MARKET))
FACTS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
              / ("hotel_policy_facts_%s.json" % MARKET))
ROUTING_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                / "identity_routing.json")
PRODUCTION_CSV = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                  / "seed_businesses.csv")
LEDGER_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "dayton_work_browser_pass_001.json")

#: Exactly what the package must contain. A missing or extra file is a gate
#: failure, not a warning -- a partial handback reconciled against a 90-row
#: queue would silently under-count.
EXPECTED_FILES: Tuple[str, ...] = tuple(
    ["batch-%03d-review.csv" % i for i in range(1, 10)]
    + ["batch-%03d-manifest.json" % i for i in range(1, 10)]
    + ["work-browser-pass-001-review.csv",
       "work-browser-pass-001-manifest.json",
       "work-browser-screenshot-queue.csv"])

EXPECTED_QUEUE_SIZE = 90

#: The classification partition the work order states as expected input.
#: Verified, not trusted: ``reconcile()`` recomputes it from the batch CSVs and
#: refuses a mismatch. Note that the headline "41 visible-policy results" in the
#: rolled-up manifest is NOT one of these buckets -- it counts rows carrying
#: policy wording, and twelve of those rows are classified
#: ROUTING_CORRECTION_PROPOSED. The two headline numbers overlap by twelve and
#: are never added together.
EXPECTED_CLASSIFICATIONS = {
    "BROWSER_VERIFIED_POLICY_VISIBLE": 29,
    "BROWSER_IDENTITY_ONLY_POLICY_NOT_VISIBLE": 26,
    "ROUTING_CORRECTION_PROPOSED": 14,
    "OFFICIAL_URL_NOT_RECOVERED": 13,
    "ACCESS_BLOCKED": 4,
    "HTTP_404": 3,
    "HTTP_5XX": 1,
}
EXPECTED_POLICY_WORDING_ROWS = 41

#: The partition the queue was BUILT against, recorded because it is no longer
#: the market's partition. PTF-DAYTON-CANDIDATE-PROMOTION-001 landed after the
#: queue was cut and moved Dayton 33 -> 44 published and 6 -> 7 no-pets, so
#: twelve of the 90 rows describe properties this market has since answered.
QUEUE_BASELINE = {"published_pet_friendly": 33, "verified_no_pets": 6,
                  "browser_review_queue": 90, "census": 129}

_COLUMNS = {
    "hotel_id": "hotel ID", "slug": "slug",
    "queued_name": "queued name", "queued_url": "queued URL",
    "final_name": "final displayed name", "final_url": "final URL",
    "address": "displayed address", "phone": "displayed phone",
    "postal_code": "displayed ZIP",
    "property_code": "visibly displayed property code",
    "policy_text": "exact visible policy wording",
    "supported": "supported facts", "withheld": "withheld facts",
    "contradictions": "contradiction or warning",
    "prior": "comparison with prior recovery result",
    "classification": "browser classification",
    "replacement_url": "proposed replacement URL",
    "identity_keys": "identity keys supporting the proposed correction",
    "screenshot_ready": "screenshot-ready",
    "next_action": "exactly one next action",
}

ROUTING_CLASSIFICATION = "ROUTING_CORRECTION_PROPOSED"
VISIBLE_POLICY_CLASSIFICATION = "BROWSER_VERIFIED_POLICY_VISIBLE"
IDENTITY_ONLY_CLASSIFICATION = "BROWSER_IDENTITY_ONLY_POLICY_NOT_VISIBLE"


class WorkBrowserInputError(RuntimeError):
    """The handback does not reconcile against the queue it claims to answer."""


# --------------------------------------------------------------------------- #
# Outcomes. Closed, mutually exclusive, and every property lands in exactly one.
# --------------------------------------------------------------------------- #

OUT_PUBLISHED = "ACCEPTED_AND_PUBLISHED_PET_FRIENDLY"
OUT_VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
OUT_ALREADY_RESOLVED = "ALREADY_RESOLVED_BEFORE_THIS_PASS"
OUT_ROUTING_CORRECTED = "IDENTITY_OR_ROUTING_CORRECTED_POLICY_UNRESOLVED"
OUT_ROUTING_REVIEW = "ROUTING_REVIEW_REQUIRED"
OUT_EVIDENCE_CANDIDATE = "EVIDENCE_CANDIDATE_AWAITING_ACCEPTED_ARTIFACT"
OUT_IDENTITY_ONLY = "IDENTITY_ONLY"
OUT_IDENTITY_BLOCKED = "IDENTITY_BLOCKED"
OUT_ACCESS_BLOCKED = "ACCESS_BLOCKED"
OUT_POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
OUT_POLICY_PARTIAL_HELD = "POLICY_PARTIAL_HELD_BY_READINESS"
OUT_CLOSURE_OR_REBRAND = "CLOSURE_OR_REBRAND_REVIEW"
OUT_MANUAL = "MANUAL_VERIFICATION_REQUIRED"

OUTCOMES = (OUT_PUBLISHED, OUT_VERIFIED_NO_PETS, OUT_ALREADY_RESOLVED,
            OUT_ROUTING_CORRECTED, OUT_ROUTING_REVIEW, OUT_EVIDENCE_CANDIDATE,
            OUT_IDENTITY_ONLY, OUT_IDENTITY_BLOCKED, OUT_ACCESS_BLOCKED,
            OUT_POLICY_NOT_FOUND, OUT_POLICY_PARTIAL_HELD,
            OUT_CLOSURE_OR_REBRAND, OUT_MANUAL)

#: Outcomes that state something about the property's pet policy.
RESOLVING_OUTCOMES = frozenset({OUT_PUBLISHED, OUT_VERIFIED_NO_PETS,
                                OUT_ALREADY_RESOLVED})


# --------------------------------------------------------------------------- #
# Reading the package.
# --------------------------------------------------------------------------- #

def input_present() -> bool:
    """True when the untracked operator package is on this machine.

    Callers declare their input as a precondition and skip with the path named,
    the pattern ``ed53d5b``/``441498d`` established after a worktree with no
    ``data/`` reported nine phantom failures.
    """
    return INPUT_DIR.is_dir() and (INPUT_DIR / EXPECTED_FILES[0]).exists()


def captures_present() -> bool:
    return any(d.is_dir() for d in CAPTURE_DIRS)


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def input_hashes(directory: Path = None) -> "OrderedDict[str, str]":
    """The 21 files and their hashes, in a fixed order.

    Hashing is preservation, not acceptance: it records precisely which
    transcription was adjudicated, so a later capture pass can be compared
    against the same words. It never makes the transcription publishable.
    """
    base = Path(directory) if directory else INPUT_DIR
    present = sorted(p.name for p in base.iterdir() if p.is_file())
    missing = [f for f in EXPECTED_FILES if f not in present]
    extra = [f for f in present if f not in EXPECTED_FILES]
    if missing or extra:
        raise WorkBrowserInputError(
            "input inventory gate: expected exactly %d files; missing=%s extra=%s"
            % (len(EXPECTED_FILES), missing, extra))
    return OrderedDict((name, sha256_file(base / name)) for name in EXPECTED_FILES)


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [{key: str(raw.get(src, "") or "").strip()
                 for key, src in _COLUMNS.items()}
                for raw in csv.DictReader(handle)]


def load_rows(directory: Path = None) -> List[Dict[str, str]]:
    """All 90 reviewed rows, one per property, from the nine batch CSVs.

    The batches are the source and the roll-up is checked against them, the same
    way round as the Cleveland pass -- a roll-up is a convenience file and a
    convenience file is not a ledger.
    """
    base = Path(directory) if directory else INPUT_DIR
    rows: List[Dict[str, str]] = []
    for number in range(1, 10):
        for row in _read_csv(base / ("batch-%03d-review.csv" % number)):
            row["batch"] = number
            rows.append(row)
    return rows


def load_rollup(directory: Path = None) -> List[Dict[str, str]]:
    base = Path(directory) if directory else INPUT_DIR
    return _read_csv(base / "work-browser-pass-001-review.csv")


# --------------------------------------------------------------------------- #
# Reconciliation.
# --------------------------------------------------------------------------- #

def reconcile(rows: Sequence[Mapping], rollup: Sequence[Mapping],
              census_slugs: Sequence[str]) -> Dict:
    """Every property accounted for exactly once, against the queue and census.

    Refuses on any of: a row count other than 90, a duplicate slug, a slug the
    Dayton census does not know, a roll-up that is not the same set as the
    batches, a classification vocabulary that is not the declared one, or a
    policy-wording count other than the declared 41.
    """
    slugs = [r["slug"] for r in rows]
    duplicates = sorted({s for s in slugs if slugs.count(s) > 1})
    if duplicates:
        raise WorkBrowserInputError("duplicate reconciliations: %s" % duplicates)
    if len(slugs) != EXPECTED_QUEUE_SIZE:
        raise WorkBrowserInputError(
            "expected %d reviewed properties, found %d"
            % (EXPECTED_QUEUE_SIZE, len(slugs)))

    known = set(census_slugs)
    unbound = sorted(s for s in slugs if s not in known)
    if unbound:
        raise WorkBrowserInputError(
            "row(s) bind to no %s census identity: %s" % (MARKET, unbound))

    rollup_slugs = [r["slug"] for r in rollup]
    if sorted(rollup_slugs) != sorted(slugs):
        raise WorkBrowserInputError(
            "the roll-up and the batches are different sets: only-in-roll-up=%s "
            "only-in-batches=%s" % (sorted(set(rollup_slugs) - set(slugs)),
                                    sorted(set(slugs) - set(rollup_slugs))))

    counts: Dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    if counts != EXPECTED_CLASSIFICATIONS:
        raise WorkBrowserInputError(
            "classification partition mismatch: expected %s, derived %s"
            % (EXPECTED_CLASSIFICATIONS, counts))

    wording = [r for r in rows if r["policy_text"].strip()]
    if len(wording) != EXPECTED_POLICY_WORDING_ROWS:
        raise WorkBrowserInputError(
            "expected %d rows carrying policy wording, found %d"
            % (EXPECTED_POLICY_WORDING_ROWS, len(wording)))
    overlap = sorted(r["slug"] for r in wording
                     if r["classification"] == ROUTING_CLASSIFICATION)

    return OrderedDict([
        ("queued", EXPECTED_QUEUE_SIZE),
        ("reconciled", len(slugs)),
        ("duplicates", 0),
        ("omissions", 0),
        ("classifications", OrderedDict(sorted(counts.items()))),
        ("rows_carrying_policy_wording", len(wording)),
        ("policy_wording_rows_also_routing_proposals", overlap),
        ("headline_overlap_note",
         "the package's headline 41 visible-policy results and 14 routing "
         "corrections overlap by %d rows and are never summed" % len(overlap)),
        ("rollup_rows", len(rollup)),
    ])


# --------------------------------------------------------------------------- #
# The evidence question, asked once for the package and then again, per row,
# against what this repository actually stores.
# --------------------------------------------------------------------------- #

ARTIFACT_CLASS = "OPERATOR_TRANSCRIBED_BROWSER_REVIEW"

ARTIFACT_VERDICT = (
    "NOT_A_PUBLICATION_GRADE_ARTIFACT_CLASS: the package carries the operator's "
    "typed record of what a browser displayed and no artifact of the surface it "
    "was read from -- its own manifest declares screenshots_created: false and "
    "no screenshots/ tree exists under the Dayton evidence directory. "
    "hotel_policy_facts_dayton-oh requires worker_result_hash, which both Dayton "
    "integrators set from a capture's html_sha256; hotel_exclusions requires "
    "source_hash; and policy_membrane M9 can only be enforced against a stored "
    "surface. Hashing the CSV binds the transcription, not the page. Every fact "
    "published by this work order is read from a hash-verified capture and none "
    "is read from the transcription.")


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def load_captures(directories: Sequence[Path] = None) -> Dict[str, Dict]:
    """Captures indexed by their own URL, with the hash re-derived.

    A capture whose ``html_sha256`` does not re-derive is dropped here rather
    than quarantined later: the artifact is the evidence, and one that does not
    match its own hash is not an artifact this module will read a fact from.
    """
    out: Dict[str, Dict] = {}
    for directory in (CAPTURE_DIRS if directories is None else directories):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                doc = json.loads(path.read_bytes().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            html = doc.get("html")
            declared = doc.get("html_sha256", "")
            if not isinstance(html, str) or not declared:
                continue
            if hashlib.sha256(html.encode("utf-8")).hexdigest() != declared:
                continue
            url = doc.get("final_url") or doc.get("url") or doc.get("requested_url") or ""
            if not url:
                continue
            record = {
                "run": directory.parent.name,
                "file": path.name,
                "url": url,
                "html": html,
                "text": doc.get("text") or "",
                "body": _norm(doc.get("text") or "") + " " + _norm(html),
                "html_sha256": declared,
            }
            out.setdefault(url.rstrip("/"), record)
            # A second key, for REPORTING only. dayton-recovery-002 names its
            # capture files by slug and the review CSV sometimes carries a
            # different URL spelling for the same page; without this the
            # corroboration count understates how much of the transcription the
            # repository can already check. Publication never uses it -- every
            # published fact is looked up by the exact URL it cites.
            out.setdefault("slug::" + path.stem, record)
    return out


def capture_for(url: str, captures: Mapping) -> Optional[Dict]:
    return captures.get((url or "").rstrip("/"))


# --------------------------------------------------------------------------- #
# Best Western's structured pets flag, measured rather than asserted.
# --------------------------------------------------------------------------- #

_BW_HOST = "bestwestern.com"

#: The survey reads WIDER than the publication path deliberately. The two
#: captures that make the boilerplate finding decisive are Columbus's -- they
#: are the artifacts PTF-NEGATIVE-EVIDENCE-P0-001 cited when it excluded two
#: properties on this flag -- and they live under the negative-evidence runner's
#: batch. Nothing here is ever read as a Dayton fact: ``load_captures()`` with
#: its default directories is what publication uses, and no entry in ``FACTS``
#: points at a URL in this extra tree.
BW_SURVEY_DIRS = CAPTURE_DIRS + (
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "discovery"
    / "review_batches" / "negative-evidence-p0-001" / "_runner" / "batch" / "captures",
)
_PETS_ALLOWED_JSON = re.compile(r'"petsAllowed"\s*:\s*(true|false)')
_PET_POLICY_BLOCK = re.compile(r"PET POLICY\s+(.{0,400}?)\s+REGISTRATION POLICY", re.S)


def best_western_pets_allowed_survey(captures: Mapping = None) -> List[Dict]:
    """Every Best Western capture on disk: the JSON-LD flag beside the visible block.

    This exists so the claim "Best Western's petsAllowed is brand boilerplate"
    is a measurement anyone can re-run, not a sentence in a docstring. It is
    also what disqualifies that flag as evidence for or against any single
    property.
    """
    caps = captures if captures is not None else load_captures(BW_SURVEY_DIRS)
    out: List[Dict] = []
    seen = set()
    for cap in sorted(caps.values(), key=lambda c: c["url"]):
        url = cap["url"]
        if registrable_domain(url) != _BW_HOST or url in seen:
            continue
        seen.add(url)
        flag = _PETS_ALLOWED_JSON.search(cap["html"])
        block = _PET_POLICY_BLOCK.search(cap["text"])
        out.append(OrderedDict([
            ("url", cap["url"]),
            ("jsonld_pets_allowed", flag.group(1) if flag else "ABSENT"),
            ("visible_pet_policy_block", _norm(block.group(1)) if block else ""),
        ]))
    return out


BW_FLAG_FINDING = (
    "Every Best Western capture in this repository carries \"petsAllowed\": "
    "false in its JSON-LD Hotel node, including the four whose visible PET "
    "POLICY block states a priced pet-friendly policy (20, 25 and 40 USD per "
    "day). A flag with one value across both the refusing property and the "
    "charging ones establishes nothing about either, so it is not authored as "
    "an establishing observation here. See best_western_pets_allowed_survey().")


# --------------------------------------------------------------------------- #
# What publishes, and the quote that establishes each field.
#
# Every quote below is asserted to be a literal substring of that property's
# hash-verified capture before any fact derived from it may publish. A field
# with no quote cannot exist here at all.
# --------------------------------------------------------------------------- #

_Q_BW_MIAMISBURG = (
    "We are Pet Friendly and allow up to two dogs in a limited number of rooms. "
    "The size limit for any one dog shall be 80 pounds. Other pet types (e.g., "
    "cats) may be allowed upon the hotel’s approval prior to arrival. The "
    "Pet Friendly rate is 20 USD per day.")
_Q_BW_WAPAKONETA = _Q_BW_MIAMISBURG.replace("is 20 USD", "is 40 USD")

_BW_WITHHELD = {
    "cats_allowed": (
        "the page says other pet types \"may be allowed upon the hotel's "
        "approval prior to arrival\" -- a conditional the property has not "
        "resolved, and a permission granted on approval is not a permission"),
    "fee_scope": (
        "the page states a rate per day and never says whether it is charged "
        "per pet or per room; the two-dog allowance does not settle it"),
    "pet_count_scope": (
        "\"in a limited number of rooms\" limits WHICH rooms accept dogs, not "
        "how many dogs a room accepts; no per-room or per-stay scope is stated"),
    "pet_deposit": (
        "the page states a nightly rate and says nothing about a deposit or "
        "about whether the rate is refundable"),
}

_Q_ESA_MAX = "A maximum of two pets are allowed in each suite."
_Q_ESA_SIZE = ("Height and length restrictions apply-- pets can be no longer "
               "than 36 inches and no taller than 36 inches.")
_ESA_WITHHELD = {
    "pet_fee": (
        "the page states a tiered non-refundable CLEANING fee -- up to $25/day "
        "for the first six (6) nights per pet, then up to $15/day per pet "
        "thereafter -- which has no single (basis, amount) pair in this schema; "
        "publishing either band alone would misstate the price of any stay of a "
        "different length. Identical treatment to the three sibling Extended "
        "Stay America records promoted by PTF-DAYTON-CANDIDATE-PROMOTION-001"),
    "weight_limit": (
        "the property restricts pets by DIMENSION (no longer and no taller than "
        "36 inches), which is not a weight limit; converting one to the other "
        "would invent a number the page does not state"),
    "species_allowed": (
        "the page says \"pets\" and names no species; \"pets\" alone is not "
        "dogs+cats"),
}

#: slug -> the record this work order publishes.
#:   ``url``      the page the fact is read from. It must equal the census
#:                ``_official_url`` when the census has one; when it does not,
#:                it must equal a ROUTING_CONFIRMED record's URL.
#:   ``facts``    field -> (published value, the quote that establishes it)
#:   ``obs``      field -> observation extraction value (money in integer cents)
FACTS: "OrderedDict[str, Dict]" = OrderedDict([

    ("best-western-plus-miamisburg-dayton", {
        "url": ("https://www.bestwestern.com/en_US/book/hotels-in-miamisburg/"
                "best-western-plus-miamisburg-dayton-suites-banquets-hotel/"
                "propertyCode.36184.html"),
        "name_on_page": "Best Western Plus Miamisburg-Dayton Suites, Banquets & Hotel",
        "source_type": "official_property_page",
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_BW_MIAMISBURG)),
            ("species_allowed", ("dogs", _Q_BW_MIAMISBURG)),
            ("pet_count_limit", ("2", _Q_BW_MIAMISBURG)),
            ("weight_limit", ("80 pounds", _Q_BW_MIAMISBURG)),
            ("pet_fee", ("$20.00", _Q_BW_MIAMISBURG)),
            ("fee_basis", ("per day", _Q_BW_MIAMISBURG)),
        ]),
        "obs": OrderedDict([
            ("pets_allowed", "true"), ("species_allowed", "dogs"),
            ("pet_count_limit", 2), ("weight_limit", "80 pounds"),
            ("pet_fee", 2000), ("fee_currency", "USD"), ("fee_basis", "per_day"),
        ]),
        "withheld": dict(_BW_WITHHELD),
    }),

    ("best-western-wapakoneta-inn", {
        "url": ("https://www.bestwestern.com/en_US/book/hotels-in-wapakoneta/"
                "best-western-wapakoneta-inn/propertyCode.36156.html"),
        "name_on_page": "Best Western Wapakoneta Inn | Wapakoneta OH Hotel",
        "source_type": "official_property_page",
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_BW_WAPAKONETA)),
            ("species_allowed", ("dogs", _Q_BW_WAPAKONETA)),
            ("pet_count_limit", ("2", _Q_BW_WAPAKONETA)),
            ("weight_limit", ("80 pounds", _Q_BW_WAPAKONETA)),
            ("pet_fee", ("$40.00", _Q_BW_WAPAKONETA)),
            ("fee_basis", ("per day", _Q_BW_WAPAKONETA)),
        ]),
        "obs": OrderedDict([
            ("pets_allowed", "true"), ("species_allowed", "dogs"),
            ("pet_count_limit", 2), ("weight_limit", "80 pounds"),
            ("pet_fee", 4000), ("fee_currency", "USD"), ("fee_basis", "per_day"),
        ]),
        "withheld": dict(_BW_WITHHELD),
    }),

    ("extended-stay-america-select-suites-dayton-miamisburg", {
        "url": "https://www.extendedstayamerica.com/hotels/oh/dayton/miamisburg",
        "name_on_page": "Extended Stay America - Dayton - Miamisburg",
        "source_type": "official_property_page",
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_ESA_MAX)),
            ("pet_count_limit", ("2", _Q_ESA_MAX)),
            ("pet_count_scope", ("room", _Q_ESA_MAX)),
            ("general_restrictions", (_Q_ESA_SIZE, _Q_ESA_SIZE)),
        ]),
        "obs": OrderedDict([
            ("pets_allowed", "true"), ("pet_count_limit", 2),
            ("pet_count_scope", "room"), ("general_restrictions", _Q_ESA_SIZE),
        ]),
        "withheld": dict(_ESA_WITHHELD),
    }),
])

#: slug -> (the affirmative refusal quote, the page it is on).
NO_PETS: "OrderedDict[str, Tuple[str, str]]" = OrderedDict([
    ("best-western-celina", (
        "Pets are not accepted.",
        "https://www.bestwestern.com/en_US/book/hotels-in-celina/"
        "best-western-celina/propertyCode.36167.html")),
])

NO_PETS_NOTE = (
    "Affirmative property-level refusal read from the visible PET POLICY block "
    "of the property's own page, in the same slot where the other four Best "
    "Western captures in this repository state a priced pet-friendly policy. "
    "The capture is the attended dayton-capture-run-001 artifact whose "
    "html_sha256 re-derives and whose final_url equals the census official_url; "
    "the ChatGPT Work browser pass transcribed the same sentence independently "
    "and is what prompted the re-read, but no fact here is taken from the "
    "transcription. The page's JSON-LD also carries \"petsAllowed\": false and "
    "that flag is deliberately NOT cited: it reads false on every Best Western "
    "page captured here, including four that charge a nightly pet rate, so it "
    "discriminates nothing. dayton_recovery_002_closeout recorded this property "
    "ACCESS_BLOCKED (\"bestwestern.com 403\") from a static fetch; the attended "
    "capture had already succeeded. Applied by "
    "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001; never held a seed row or a policy "
    "record."
)


# --------------------------------------------------------------------------- #
# Observations, so the readiness gate rules on this batch rather than on a
# neighbouring one.
# --------------------------------------------------------------------------- #

def _hotel_ref(hotel: Mapping, url: str) -> Dict:
    ref = {
        "market_id": MARKET,
        "canonical_name": hotel["canonical_name"],
        "normalized_name": hotel["normalized_name"],
    }
    if hotel.get("street_identity"):
        ref["street_identity"] = hotel["street_identity"]
    if url:
        ref["official_url"] = url
    if hotel.get("_property_code"):
        ref["property_code"] = hotel["_property_code"]
    return ref


def build_observations(census: Mapping, captures: Mapping) -> List[Dict]:
    """One validated observation per identity this work order rules on.

    Built from the capture, never from the transcription: the quote is asserted
    present in the capture body before the observation is emitted.
    """
    batch: List[Dict] = []

    for slug, spec in FACTS.items():
        hotel = census[slug]
        cap = capture_for(spec["url"], captures)
        if cap is None:
            raise WorkBrowserInputError(
                "%s: no hash-verified capture of %s" % (slug, spec["url"]))
        # quote -> the fields that quote establishes. Built from the facts
        # table so an evidence entry claims the fields it actually covers
        # rather than all of them; M9 would pass either way, and "either way"
        # is how a record starts describing a page it never read.
        quotes: "OrderedDict[str, List[str]]" = OrderedDict()
        for field, (_value, quote) in spec["facts"].items():
            quotes.setdefault(quote, []).append(field)
        for quote in quotes:
            if _norm(quote) not in cap["body"]:
                raise WorkBrowserInputError(
                    "%s: quote is not in its capture -- %r" % (slug, quote))
        extraction = dict(spec["obs"])
        # Extraction names the observation contract carries that the published
        # facts table does not (``fee_currency``). They come from the same
        # sentence as the fee, which is the first quote in the table.
        extra = sorted(set(extraction) - set(spec["facts"]))
        first = next(iter(quotes))
        quotes[first] = sorted(set(quotes[first]) | set(extra))
        batch.append({
            "obs_id": "%s-001" % slug,
            "contract_version": PO.CONTRACT_VERSION,
            "hotel_ref": _hotel_ref(hotel, spec["url"]),
            "identity_check": {"name_on_page": spec["name_on_page"],
                               "address_on_page": hotel["address"],
                               "phone_on_page": hotel["phone"]},
            "source_url": spec["url"],
            "source_type": spec["source_type"],
            "authority_tier": PO.SOURCE_TYPE_MAX_TIER[spec["source_type"]],
            "observed_at": AS_OF,
            "retrieved_at": AS_OF + "T00:00:00Z",
            "capture_method": "browser_assisted",
            "evidence": [{"quote": quote, "location": "PET POLICY block",
                          "field_refs": fields}
                         for quote, fields in quotes.items()],
            "extraction": extraction,
            "extraction_confidence": "EXACT_QUOTE",
            "flags": [],
        })

    for slug, (quote, url) in NO_PETS.items():
        hotel = census[slug]
        cap = capture_for(url, captures)
        if cap is None:
            raise WorkBrowserInputError(
                "%s: no hash-verified capture of %s" % (slug, url))
        if _norm(quote) not in cap["body"]:
            raise WorkBrowserInputError(
                "%s: refusal quote is not in its capture -- %r" % (slug, quote))
        batch.append({
            "obs_id": "%s-001" % slug,
            "contract_version": PO.CONTRACT_VERSION,
            "hotel_ref": _hotel_ref(hotel, url),
            "identity_check": {"name_on_page": "Celina Ohio Hotels | Best Western Celina",
                               "address_on_page": hotel["address"],
                               "phone_on_page": hotel["phone"]},
            "source_url": url,
            "source_type": "official_property_page",
            "authority_tier": PO.SOURCE_TYPE_MAX_TIER["official_property_page"],
            "observed_at": AS_OF,
            "retrieved_at": AS_OF + "T00:00:00Z",
            "capture_method": "browser_assisted",
            "evidence": [{"quote": quote, "location": "PET POLICY block",
                          "field_refs": ["pets_allowed"]}],
            "extraction": {"pets_allowed": False},
            "extraction_confidence": "EXACT_QUOTE",
            "flags": [],
        })

    return PO.validate_emission_batch(batch)


def readiness_by_slug(observations: Sequence[Mapping]) -> Dict[str, "RD.ReadinessResult"]:
    by_slug: Dict[str, List[Dict]] = {}
    for obs in observations:
        by_slug.setdefault(obs["obs_id"].rsplit("-", 1)[0], []).append(obs)
    return {slug: RD.derive(obs_list) for slug, obs_list in by_slug.items()}


# --------------------------------------------------------------------------- #
# Routing adjudication. Hand-authored, one entry per proposal, and every
# decision names the criterion it met or failed rather than a mood.
#
# Dayton held ZERO routing records before this work order -- the registry
# carried only Columbus and Cleveland -- and the census has no _official_url for
# any of these fourteen. So none of these is a "correction": each is a
# first-time route binding, which is why the bar applied is the same
# two-independent-key bar identity_keys applies everywhere and not a lower one
# for "it was already nearly right".
# --------------------------------------------------------------------------- #

ACCEPTED = "ACCEPTED"
HELD = "HELD"
REJECTED = "REJECTED"

#: slug -> (decision, status, reason, one next action)
ROUTING_ADJUDICATION: "OrderedDict[str, Tuple[str, str, str, str]]" = OrderedDict([

    ("extended-stay-america-select-suites-dayton-miamisburg", (
        ACCEPTED, ROUTING_CONFIRMED,
        "Verified first-party, not on the transcription's word: the proposed "
        "URL answers a plain GET, and the page itself carries the census street "
        "token \"Summit Glen\" and postal code 45449 alongside a JSON-LD Hotel "
        "node whose @id is the URL. Two independent identity keys read from the "
        "destination, on the brand's own registrable domain, and no other "
        "identity owns the URL.",
        "None outstanding: the route is bound and the policy this page states "
        "is published by this same work order.")),

    ("golden-inn-new-paris", (
        ACCEPTED, ROUTING_CONFIRMED,
        "Verified first-party: the proposed URL answers a plain GET and the "
        "page carries the census telephone 937-437-0722 and the city New Paris "
        "under the property's own title \"The Golden Inn\". Phone plus locality "
        "read from the destination itself. The census identity is still "
        "IDENTITY_PROVISIONAL, which is why the route binds and no policy "
        "publishes.",
        "Confirm the census identity for Golden Inn New Paris (street 8868 US "
        "40 W and postal code 45347 appear nowhere on the property's page); the "
        "pet fee it states may publish only after identity is confirmed.")),

    ("comfort-suites-springfield-i-70", (
        HELD, ROUTING_HELD,
        "The transcription reports name, street 121 Raydo Circle and ZIP 45506 "
        "agreeing with the census, which would be two independent keys -- but "
        "the destination could not be read here: choicehotels.com returns no "
        "response at all (read timeout at 25s and again at 60s), the same "
        "silent-timeout pattern every Choice fetch in this repository "
        "reproduces. No key could be verified against the page.",
        "Attended capture of the proposed choicehotels.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("holiday-inn-express-suites-greenville", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 1195 Russ Road and ZIP 45331 "
        "agreeing; ihg.com returned HTTP 403 to a direct fetch, so nothing was "
        "read from the destination.",
        "Attended capture of the proposed ihg.com URL; the route is recorded "
        "HELD until one identity key is read from the page itself.")),

    ("quality-inn-greenville", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 1190 Russ Road and ZIP 45331 "
        "agreeing; choicehotels.com timed out with no response.",
        "Attended capture of the proposed choicehotels.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("quality-inn-sidney", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 1959 Michigan Street and ZIP 45365 "
        "agreeing; choicehotels.com timed out with no response. The census "
        "identity is also still IDENTITY_PROVISIONAL.",
        "Attended capture of the proposed choicehotels.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("red-roof-inn-dayton-fairborn-nutter-center", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 2580 Colonel Glenn Hwy and ZIP "
        "45324 agreeing; redroof.com returned HTTP 403 to a direct fetch.",
        "Attended capture of the proposed redroof.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("red-roof-inn-dayton-north-airport", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 7370 Miller Ln and ZIP 45414 "
        "agreeing; redroof.com returned HTTP 403 to a direct fetch.",
        "Attended capture of the proposed redroof.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("red-roof-inn-dayton-south-miamisburg", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 222 Byers Rd and ZIP 45342 "
        "agreeing; redroof.com returned HTTP 403 to a direct fetch.",
        "Attended capture of the proposed redroof.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("red-roof-inn-springfield", (
        HELD, ROUTING_HELD,
        "Transcription reports name, street 155 West Leffel Lane and ZIP 45505 "
        "agreeing; redroof.com returned HTTP 403 to a direct fetch.",
        "Attended capture of the proposed redroof.com URL; the route is "
        "recorded HELD until one identity key is read from the page itself.")),

    ("holiday-inn-express-suites-springfield", (
        REJECTED, "",
        "One key only. The census row carries NO street address at all, so the "
        "single offered key is the property name -- and \"Holiday Inn Express & "
        "Suites Springfield\" is a name a brand uses in many Springfields. The "
        "destination returned HTTP 403, so nothing could be read from it "
        "either. A name alone has never bound a route here.",
        "Recover a street address for this census row first (identity is the "
        "blocker, not the URL), then re-propose the ihg.com route.")),

    ("quality-inn-springfield", (
        REJECTED, "",
        "One key only, for the same reason: the census row carries no street "
        "address, and Springfield OH 45506 already holds another census "
        "identity in this same batch (Comfort Suites Springfield I-70). "
        "Binding a route on a shared city and a brand name is how two "
        "properties end up sharing one endpoint.",
        "Recover a street address for this census row first, then re-propose "
        "the choicehotels.com route.")),

    ("comfort-inn-washington-court-house", (
        REJECTED, "",
        "The proposal disagrees with the identity on two axes at once. The "
        "census row is Comfort Inn Washington Court House; the recovered page "
        "visibly identifies Quality Inn Washington Court House, and the URL "
        "path is /ohio/jeffersonville/, a different municipality. Neither the "
        "brand nor the city agrees, and the census row carries no street "
        "address to arbitrate with.",
        "Determine whether the Washington Court House census row and the "
        "Jeffersonville Quality Inn are the same property before any route is "
        "bound; if they are not, the census row needs its own URL.")),

    ("hotel-piqua-east-ash", (
        REJECTED, "",
        "A rebrand candidate, not a routing correction. Street 950 E Ash Street "
        "and ZIP 45356 agree, but the page visibly identifies \"Comfort Inn & "
        "Suites Piqua-Near Troy-I75\" while the census row is \"Hotel Piqua "
        "East Ash\". This is exactly the case M10 refuses to let an address "
        "override -- an address is a place and a name is a business, and one "
        "building can change hands.",
        "Confirm whether Hotel Piqua East Ash rebranded to Comfort Inn & Suites "
        "Piqua and record the identity continuity on the census row; only then "
        "may the choicehotels.com route bind.")),
])

#: The provenance of the two routes accepted on a fetch made by this work order.
_ACCEPTED_ROUTE_EVIDENCE = {
    "extended-stay-america-select-suites-dayton-miamisburg": (
        "https://www.extendedstayamerica.com/hotels/oh/dayton/miamisburg",
        "sha256:78679c26c662a192e22ba7e510828a4ca00398ed847abf8f8f6c3d60dfafb5ef",
        ("page_street_token=Summit Glen", "page_postal_code=45449",
         "jsonld_Hotel_@id=https://www.extendedstayamerica.com/hotels/oh/dayton/miamisburg",
         "jsonld_name=Extended Stay America - Dayton - Miamisburg"),
        "EXTENDED_STAY_AMERICA"),
    "golden-inn-new-paris": (
        "https://thegoldeninn.com/",
        "sha256:ead0a162db238300dd7dce2b2a42030243294a785a9b8bbc06ea961a8e40b326",
        ("page_telephone=937-437-0722", "page_locality=New Paris",
         "page_title=The Golden Inn"),
        "INDEPENDENT"),
}

#: Brand label for a HELD route, taken from the census annotation so it is not
#: invented at the registry layer.
_BRAND_LABEL = {
    "bestwestern": "BEST_WESTERN", "choicehotels": "CHOICE", "ihg": "IHG",
    "redroof": "RED_ROOF", "marriott": "MARRIOTT", "hilton": "HILTON",
    "wyndham": "WYNDHAM", "extendedstay": "EXTENDED_STAY_AMERICA",
    "radisson": "RADISSON", "sonesta": "SONESTA", "other": "INDEPENDENT",
}


def _routing_id(slug: str) -> str:
    return "route-%s-%s" % (MARKET, slug)


def build_routing_records(census: Mapping, rows_by_slug: Mapping,
                          seed_keys: Sequence[str] = ()) -> List[Dict]:
    """The routing records this work order writes, validated one by one.

    ``seed_keys`` are the normalized names the seed already carries. A route is
    the mechanism for a CONFIRMED identity that is NOT inventory, and
    ``test_no_committed_route_is_already_seed_inventory`` enforces exactly that:
    a surviving route for a seeded hotel is a second, competing authority for
    the same identity. Extended Stay America Select Suites Dayton - Miamisburg
    is adjudicated ACCEPTED here -- its URL is verified and that is what let its
    policy publish -- and precisely because it publishes, the seed becomes the
    authority for it and no routing record is written.
    """
    seeded = set(seed_keys)
    records: List[Dict] = []
    for slug, (decision, status, reason, action) in ROUTING_ADJUDICATION.items():
        if decision == REJECTED:
            continue
        hotel = census[slug]
        if normalize_name(hotel["canonical_name"]) in seeded:
            continue
        row = rows_by_slug[slug]
        url = row["replacement_url"] or row["final_url"]
        brand = _BRAND_LABEL.get((hotel.get("_brand") or "other").lower(),
                                 "INDEPENDENT")
        record: "OrderedDict[str, object]" = OrderedDict([
            ("routing_id", _routing_id(slug)),
            ("schema_version", "1.0.0"),
            ("hotel_ref", OrderedDict([
                ("market_id", MARKET),
                ("canonical_name", hotel["canonical_name"]),
                ("normalized_name", normalize_name(hotel["canonical_name"])),
            ])),
            ("market_id", MARKET),
            ("official_property_url", url),
            ("official_domain", registrable_domain(url)),
            ("brand", brand),
            # PAGE_RENDERED means the property served US its page. Only the
            # accepted routes can say that; the held ones were recovered from
            # the brand's own property-code index and their destinations
            # answered this work order with 403 or with nothing at all, which
            # is BRAND_INDEX_BINDING and is what
            # ``test_every_committed_record_preserves_index_binding`` refuses
            # to let a bot-walled brand relabel.
            ("binding_method", BINDING_PAGE_RENDERED if decision == ACCEPTED
             else BINDING_BRAND_INDEX),
            ("binding_sources", []),
            ("observed_at", AS_OF),
            ("verified_at", AS_OF),
            ("status", status),
        ])
        if hotel.get("street_identity"):
            record["hotel_ref"]["street_identity"] = hotel["street_identity"]

        if decision == ACCEPTED:
            _url, digest, signals, _brand = _ACCEPTED_ROUTE_EVIDENCE[slug]
            record["binding_sources"] = [
                "%s fetched %s during %s (plain HTTPS GET; no challenge solved, "
                "no bot defence circumvented) html_sha256=%s"
                % (url, AS_OF, WORK_ORDER, digest)]
            record["identity_signals_matched"] = list(signals)
            record["property_identity_check"] = "PASS"
        else:
            record["binding_sources"] = [
                "ChatGPT Work browser review %s (operator transcription; the "
                "destination could not be read by this work order) -- reported "
                "name, street and postal code agreement with the census"
                % "work-browser-pass-001"]
            record["identity_signals_matched"] = [
                s.strip() for s in (row["identity_keys"] or "").split(";") if s.strip()]

        record["identity_context"] = OrderedDict(
            (k, v) for k, v in (("address", hotel.get("address", "")),
                                ("city", hotel.get("city", "")),
                                ("state", hotel.get("state", "")),
                                ("postal_code", hotel.get("postal_code", "")),
                                ("phone", hotel.get("phone", ""))) if v)
        record["notes"] = "%s: %s Next action: %s" % (WORK_ORDER, reason, action)
        if hotel.get("_property_code"):
            record["property_code"] = str(hotel["_property_code"])
        validate_record(record)
        records.append(record)
    return records


# --------------------------------------------------------------------------- #
# Per-property outcome. Ordered so the first matching rule wins, strongest
# statement first.
# --------------------------------------------------------------------------- #

#: Rows whose transcribed wording states a refusal. Recorded as what they are:
#: scoring any of them as a permission would queue a no-pets hotel as
#: pet-friendly, and every one of them is held for the same missing artifact as
#: the affirmative rows.
_NEGATIVE = re.compile(
    r"pets\s+allowed:\s*no|no\s+pets\s+allowed|pets\s+(?:are\s+)?not\s+"
    r"(?:accepted|allowed|permitted)", re.I)
_SERVICE_ANIMAL_ONLY = re.compile(
    r"only\s+service\s+animals\s+are\s+permitted", re.I)
_AFFIRMATIVE = re.compile(
    r"pets?\s+(?:are\s+)?(?:allowed|welcome|permitted)|pet[-\s]friendly"
    r"|dogs?\s+(?:are\s+)?(?:allowed|welcome)|dog\s+friendly|pet\s+policy:"
    r"|pet\s+accommodation", re.I)
_STRUCTURED = (
    re.compile(r"\$\s?\d|\b\d+(?:\.\d+)?\s*usd\b|\bfee\b", re.I),
    re.compile(r"\b\d+\s*(?:lb|lbs|pound)|weight limit|size limit", re.I),
    re.compile(r"maximum of \d+|up to (?:two|three|\d+)|pet limit", re.I),
)


def policy_shape(text: str) -> str:
    """What the transcribed wording says, independent of whether it may publish."""
    body = (text or "").strip()
    if not body:
        return "NONE"
    negative = bool(_NEGATIVE.search(body))
    affirmative = bool(_AFFIRMATIVE.search(body))
    if negative and _SERVICE_ANIMAL_ONLY.search(body):
        return "NEGATIVE_WITH_SERVICE_ANIMAL_EXCEPTION"
    if negative and affirmative:
        return "CONTRADICTORY"
    if negative:
        return "NEGATIVE"
    if not affirmative:
        return "NONE"
    return ("AFFIRMATIVE_STRUCTURED"
            if any(p.search(body) for p in _STRUCTURED)
            else "AFFIRMATIVE_MARKETING_ONLY")


#: Rows the census marks IDENTITY_PROVISIONAL. Identity is the blocker there,
#: and a policy may not attach to an identity that is not settled.
def _identity_blocked(hotel: Mapping) -> bool:
    return hotel.get("identity_state") != "IDENTITY_CONFIRMED"


def outcome_for(row: Mapping, hotel: Mapping, *, published: bool, excluded: bool,
                captures: Mapping) -> Tuple[str, str, str]:
    """(outcome, reason_code, next_action) for one reviewed property."""
    slug = row["slug"]

    if slug in FACTS:
        return (OUT_PUBLISHED, "PUBLISHED_FROM_A_HASH_VERIFIED_CAPTURE",
                "None outstanding: the pet policy is committed authority.")
    if slug in NO_PETS:
        return (OUT_VERIFIED_NO_PETS, "EXCLUDED_FROM_A_HASH_VERIFIED_CAPTURE",
                "None outstanding: the refusal is committed authority.")
    if published:
        return (OUT_ALREADY_RESOLVED, "PUBLISHED_BY_PTF_DAYTON_CANDIDATE_PROMOTION_001",
                "None outstanding: this row was queued against the 33/6 "
                "baseline and the market answered it before this pass ran.")
    if excluded:
        return (OUT_ALREADY_RESOLVED, "EXCLUDED_BY_PTF_DAYTON_CANDIDATE_PROMOTION_001",
                "None outstanding: this row was queued against the 33/6 "
                "baseline and the market answered it before this pass ran.")

    if row["classification"] == ROUTING_CLASSIFICATION:
        decision, _status, _reason, action = ROUTING_ADJUDICATION[slug]
        if decision == ACCEPTED:
            return OUT_ROUTING_CORRECTED, "ROUTE_BOUND_ON_FIRST_PARTY_PROOF", action
        if decision == HELD:
            return OUT_ROUTING_REVIEW, "ROUTE_RECORDED_HELD_DESTINATION_UNREADABLE", action
        return OUT_CLOSURE_OR_REBRAND if slug in ("hotel-piqua-east-ash",
                                                  "comfort-inn-washington-court-house") \
            else OUT_ROUTING_REVIEW, "ROUTING_PROPOSAL_REJECTED", action

    if slug in ("baymont-by-wyndham-dayton-north", "wingate-by-wyndham-dayton-north"):
        return (OUT_POLICY_PARTIAL_HELD, "READINESS_POLICY_PARTIAL",
                "Capture the property's formal pet-policy template; the only "
                "first-party sentence is a marketing blurb that "
                "readiness.derive holds at POLICY_PARTIAL, and "
                "PUBLISHABLE_STATES excludes it.")

    if row["classification"] == IDENTITY_ONLY_CLASSIFICATION:
        return (OUT_IDENTITY_ONLY, "PAGE_RENDERED_NO_PET_POLICY_STATED",
                "Capture the property's pet-policy surface (accordion, modal or "
                "amenities page) that the overview page does not render.")
    if row["classification"] == "OFFICIAL_URL_NOT_RECOVERED":
        return (OUT_IDENTITY_BLOCKED, "NO_FIRST_PARTY_URL_ON_RECORD",
                "Recover a first-party property URL from a brand locator or a "
                "CVB anchor; no evidence capture is possible until one exists.")
    if row["classification"] == "ACCESS_BLOCKED":
        return (OUT_ACCESS_BLOCKED, "BRAND_PLATFORM_REFUSED_THE_BROWSER",
                "Re-attempt in an attended browser under capture_automation "
                "doctrine pacing; no challenge may be solved programmatically.")
    if row["classification"] == "HTTP_404":
        return (OUT_MANUAL, "OFFICIAL_URL_RETURNS_404",
                "Re-resolve this property's official URL from a first-party "
                "surface; the URL on record is dead.")
    if row["classification"] == "HTTP_5XX":
        return (OUT_MANUAL, "OFFICIAL_URL_RETURNS_5XX",
                "Re-attempt the URL later and, if it stays down, resolve an "
                "alternate first-party endpoint.")

    # --- the rows that rendered something about pets ----------------------- #
    shape = policy_shape(row["policy_text"])
    has_capture = capture_for(row["final_url"] or row["queued_url"], captures) is not None
    if _identity_blocked(hotel):
        return (OUT_IDENTITY_BLOCKED, "CENSUS_IDENTITY_IS_PROVISIONAL",
                "Confirm this census identity before any policy attaches to "
                "it; a transcribed policy on a provisional identity states "
                "nothing about a hotel we can name.")
    if shape in ("NEGATIVE", "NEGATIVE_WITH_SERVICE_ANIMAL_EXCEPTION"):
        return (OUT_EVIDENCE_CANDIDATE, "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT",
                "Capture the refusal sentence on the property's own page; "
                "hotel_exclusions requires source_hash and the transcription "
                "supplies none%s."
                % (" (a capture of this URL exists but does not contain the "
                   "transcribed sentence)" if has_capture else ""))
    if shape == "CONTRADICTORY":
        return (OUT_MANUAL, "TRANSCRIBED_WORDING_BOTH_PERMITS_AND_REFUSES",
                "Capture both conflicting surfaces so approval_resolution can "
                "adjudicate; this layer never selects a winner (M8).")
    if shape in ("AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_MARKETING_ONLY"):
        return (OUT_EVIDENCE_CANDIDATE, "AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT",
                "Capture the pet-policy block on the property's own page; every "
                "publication route requires a sha256 of the page and the "
                "transcription supplies none%s."
                % (" (a capture of this URL exists but does not contain the "
                   "transcribed sentence)" if has_capture else ""))
    return (OUT_POLICY_NOT_FOUND, "PET_WORDING_TRANSCRIBED_ESTABLISHES_NOTHING",
            "Capture the property's pet-policy surface; the transcribed "
            "wording neither permits nor refuses pets.")


# --------------------------------------------------------------------------- #
# Cross-market findings. Reported, never acted on from here.
# --------------------------------------------------------------------------- #

CROSS_MARKET_FINDINGS = [OrderedDict([
    ("market_id", "columbus-oh"),
    ("finding",
     "Two Columbus properties are VERIFIED_NO_PETS on evidence their own "
     "retained captures contradict. excl-best-western-canal-winchester-inn-"
     "columbus-south-east and excl-best-western-executive-inn were applied by "
     "PTF-NEGATIVE-EVIDENCE-P0-001 citing '\"petsAllowed\": false', and the "
     "captures those exclusions name (source_hash 80f297b0... and fcb40704...) "
     "each contain a visible PET POLICY block reading \"We are Pet Friendly and "
     "allow up to two dogs ... The Pet Friendly rate is 40 USD per day\" and "
     "\"25.00 USD per day\" respectively. The JSON-LD flag reads false on all "
     "five Best Western captures in this repository, four of which state a "
     "priced pet-friendly policy, so it is brand boilerplate rather than a "
     "property fact."),
    ("scope_decision",
     "Not acted on here. Columbus is frozen (PTF-COLUMBUS-FREEZE-DEPLOY-001) "
     "and this work order is required to leave its bundle byte-identical; no "
     "Columbus file is touched."),
    ("affected_exclusion_ids",
     ["excl-best-western-canal-winchester-inn-columbus-south-east",
      "excl-best-western-executive-inn"]),
    ("next_action",
     "Open a Columbus work order to re-adjudicate both exclusions against the "
     "visible PET POLICY block in their own retained captures, and to review "
     "whether any other structured_pets_allowed_false exclusion rests on a "
     "brand-invariant flag. Hotel Versailles (dayton-oh) also used this "
     "evidence shape but its page carries no visible pet text at all, so it is "
     "not contradicted by its own capture."),
])]


# --------------------------------------------------------------------------- #
# Build.
# --------------------------------------------------------------------------- #

def _read_json(path: Path) -> Dict:
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def _write_lf(path: Path, text: str) -> None:
    """LF endings, explicitly -- ``launch_packages/**`` is pinned ``eol=lf``."""
    path.write_bytes(text.encode("utf-8"))


def load_census() -> Dict[str, Dict]:
    return {h["slug"]: h for h in _read_json(CENSUS_PATH)["hotels"]}


def _policy_block(cap: Mapping, quotes: Sequence[str]) -> str:
    """The property's own policy text, whitespace-collapsed.

    Same invariant as the other two Dayton integrators: EVERY quote published
    must be inside the returned block, because that is what the published
    record's ``evidence_quote`` and the seed row's ``pet_policy`` carry.
    """
    body = cap["body"]
    spans = []
    for quote in quotes:
        needle = _norm(quote)
        i = body.find(needle)
        if i >= 0:
            spans.append((i, i + len(needle)))
    if not spans:
        return ""
    start, end = min(s for s, _ in spans), max(e for _, e in spans)
    if end - start <= 900:
        return body[start:end].strip()
    seen, ordered = set(), []
    for _i, quote in sorted(zip([s for s, _ in spans], quotes)):
        text = _norm(quote)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return " ".join(ordered)


def build_records(census: Mapping, captures: Mapping,
                  states: Mapping) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """(published facts, exclusions, quarantined) -- nothing is written."""
    accepted: List[Dict] = []
    exclusions: List[Dict] = []
    quarantined: List[Dict] = []

    for slug, spec in FACTS.items():
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        if hotel["identity_state"] != "IDENTITY_CONFIRMED":
            quarantined.append({"slug": slug,
                                "reason": "identity_state is %s, not IDENTITY_CONFIRMED"
                                          % hotel["identity_state"]})
            continue
        cap = capture_for(spec["url"], captures)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no hash-verified capture of %s" % spec["url"]})
            continue
        census_url = hotel.get("_official_url", "")
        if census_url and census_url.rstrip("/") != spec["url"].rstrip("/"):
            quarantined.append({"slug": slug,
                                "reason": "capture URL %r is not the census "
                                          "official_url %r" % (spec["url"], census_url)})
            continue
        if not census_url:
            route = ROUTING_ADJUDICATION.get(slug)
            if not route or route[0] != ACCEPTED:
                quarantined.append({"slug": slug,
                                    "reason": "the census has no official_url and no "
                                              "ROUTING_CONFIRMED record binds this URL"})
                continue
        state = states.get(slug)
        if state is None:
            quarantined.append({"slug": slug,
                                "reason": "no observation derives a readiness state"})
            continue
        if state.state not in RD.PUBLISHABLE_STATES:
            quarantined.append({"slug": slug,
                                "reason": "readiness state %s is not in "
                                          "PUBLISHABLE_STATES %s"
                                          % (state.state, sorted(RD.PUBLISHABLE_STATES))})
            continue

        facts: "OrderedDict[str, object]" = OrderedDict()
        evidence: List[Dict] = []
        bad: List[str] = []
        for field, (value, quote) in spec["facts"].items():
            if _norm(quote) not in cap["body"]:
                bad.append("%s: quote is not in the captured page -- %r" % (field, quote))
                continue
            evidence.append(OrderedDict([("field", field), ("quote", quote),
                                         ("source_url", spec["url"]),
                                         ("value", value)]))
            facts[field] = value
        if bad:
            quarantined.append({"slug": slug, "reason": "; ".join(bad)})
            continue

        block = _policy_block(cap, [e["quote"] for e in evidence])
        missing = [e["field"] for e in evidence
                   if _norm(e["quote"]).lower() not in _norm(block).lower()]
        if missing:
            quarantined.append({"slug": slug,
                                "reason": "policy block does not contain the quote for %s"
                                          % ", ".join(missing)})
            continue
        overlap = set(facts) & set(spec.get("withheld", {}))
        if overlap:
            quarantined.append({"slug": slug,
                                "reason": "field(s) both published and withheld: %s"
                                          % ", ".join(sorted(overlap))})
            continue

        accepted.append(OrderedDict([
            ("key", normalize_name(hotel["canonical_name"])),
            ("name", hotel["canonical_name"]),
            ("facts", facts),
            ("evidence", evidence),
            ("evidence_count", len(evidence)),
            ("evidence_quote", block),
            ("source_url", spec["url"]),
            ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", AS_OF), ("verified_at", AS_OF),
            ("approval", OrderedDict([("approval_date", AS_OF),
                                      ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
                                      ("operator", REVIEWER)])),
            ("withheld_fields", OrderedDict(sorted(spec.get("withheld", {}).items()))),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash", cap["html_sha256"]),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
        ]))

    for slug, (quote, url) in NO_PETS.items():
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        cap = capture_for(url, captures)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no hash-verified capture for a negative fact"})
            continue
        if _norm(quote) not in cap["body"]:
            quarantined.append({"slug": slug,
                                "reason": "refusal quote is not in the captured page"})
            continue
        state = states.get(slug)
        if state is None or state.state != RD.POLICY_NEGATIVE_CONFIRMED:
            quarantined.append({"slug": slug,
                                "reason": "readiness derives %r, not POLICY_NEGATIVE_CONFIRMED"
                                          % (None if state is None else state.state)})
            continue
        rec = OrderedDict([
            ("exclusion_id", "day-%s" % slug),
            ("canonical_name", hotel["canonical_name"]),
            ("normalized_name", normalize_name(hotel["canonical_name"])),
            ("address", hotel.get("address", "")),
            ("city", hotel.get("city", "")), ("state", hotel.get("state", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("official_url", url),
            ("exclusion_state", EX.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", url),
            ("observed_at", AS_OF),
            ("source_hash", cap["html_sha256"]),
            ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
            ("notes", NO_PETS_NOTE), ("market_id", MARKET),
        ])
        rec["record_hash"] = EX.record_hash(rec)
        rec["approval_hash"] = EX.approval_hash(rec)
        exclusions.append(rec)

    return accepted, exclusions, quarantined


def seed_rows(accepted: Sequence[Mapping], census: Mapping) -> List[Dict]:
    by_key = {normalize_name(h["canonical_name"]): h for h in census.values()}
    by_key_url = {normalize_name(census[s]["canonical_name"]): spec["url"]
                  for s, spec in FACTS.items()}
    rows = []
    for rec in accepted:
        hotel = by_key[rec["key"]]
        url = by_key_url[rec["key"]]
        rows.append({
            "name": hotel["canonical_name"], "category": CATEGORY,
            "address": hotel.get("address", ""), "city": hotel.get("city", ""),
            "state": hotel.get("state", ""),
            "postal_code": hotel.get("postal_code", ""),
            "phone": hotel.get("phone", ""),
            "website_url": url, "source_url": url,
            "source_type": "OFFICIAL_PROPERTY", "observed_at": AS_OF,
            "rating": "", "amenities": "",
            # The renderability boundary reads this field: empty means "pending
            # attestation" and the listing is filtered out before the WGE.
            "pet_policy": rec["evidence_quote"],
            "canonical": "", MARKET_ID_FIELD: MARKET,
        })
    return rows


def seed_keys(extra: Sequence[str] = ()) -> List[str]:
    """Normalized names the seed carries, plus the ones about to be added."""
    with PRODUCTION_CSV.open("r", encoding="utf-8", newline="") as fh:
        names = [normalize_name(r["name"]) for r in csv.DictReader(fh)
                 if r.get("category") == CATEGORY]
    return names + list(extra)


def build(directory: Path = None) -> Dict:
    """The whole adjudication, derived. Nothing below is typed twice."""
    rows = load_rows(directory)
    census = load_census()
    reconciliation = reconcile(rows, load_rollup(directory), list(census))

    captures = load_captures()
    observations = build_observations(census, captures)
    states = readiness_by_slug(observations)
    accepted, exclusions, quarantined = build_records(census, captures, states)
    if quarantined:
        raise WorkBrowserInputError(
            "refusing %d record(s):\n%s"
            % (len(quarantined),
               "\n".join("  %(slug)s: %(reason)s" % q for q in quarantined)))

    # "Before" means before THIS pass, not before the file was written. Taking
    # it straight off the authority would make the ledger say something
    # different once it had been applied -- the three records it published would
    # read as ALREADY_RESOLVED on the next build -- so the pass's own additions
    # are subtracted out and ``build()`` is the same document either side of a
    # write. ``test_rebuilding_reproduces_the_committed_ledger`` is what holds
    # this.
    facts_doc = _read_json(FACTS_PATH)
    mine_published = {r["key"] for r in accepted}
    mine_excluded = {r["normalized_name"] for r in exclusions}
    published_before = {h["key"] for h in facts_doc["hotels"]} - mine_published
    exclusion_records = EX.load_exclusions()
    excluded_before = {normalize_name(r["canonical_name"]) for r in exclusion_records
                       if r.get("market_id") == MARKET
                       and r["exclusion_state"] == EX.VERIFIED_NO_PETS} - mine_excluded
    published_after = published_before | mine_published
    excluded_after = excluded_before | mine_excluded

    rows_by_slug = {r["slug"]: r for r in rows}
    routing_records = build_routing_records(
        census, rows_by_slug, seed_keys([r["key"] for r in accepted]))

    items: List[Dict] = []
    for row in sorted(rows, key=lambda r: r["slug"]):
        hotel = census[row["slug"]]
        key = normalize_name(hotel["canonical_name"])
        outcome, reason, action = outcome_for(
            row, hotel, published=key in published_before,
            excluded=key in excluded_before, captures=captures)
        items.append(OrderedDict([
            ("slug", row["slug"]),
            ("canonical_name", hotel["canonical_name"]),
            ("market_id", MARKET),
            ("batch", row["batch"]),
            ("browser_classification", row["classification"]),
            ("outcome", outcome),
            ("reason_code", reason),
            ("next_action", action),
            ("identity_state", hotel["identity_state"]),
            ("policy_wording_shape", policy_shape(row["policy_text"])),
            ("transcribed_policy_wording", row["policy_text"]),
            ("transcription_corroborated_by_a_stored_capture",
             _corroborated(row, captures)),
            ("source_url", row["final_url"] or row["queued_url"]),
            ("published_before", key in published_before),
            ("published_after", key in published_after),
            ("verified_no_pets_before", key in excluded_before),
            ("verified_no_pets_after", key in excluded_after),
        ]))

    outcome_counts = OrderedDict(
        (name, sum(1 for i in items if i["outcome"] == name)) for name in OUTCOMES)
    census_total = len(census)
    reconciled = OrderedDict([
        ("census", census_total),
        ("published_pet_friendly", len(published_after)),
        ("verified_no_pets", len(excluded_after)),
        ("resolved", len(published_after) + len(excluded_after)),
        ("unresolved_or_held",
         census_total - len(published_after) - len(excluded_after)),
    ])
    if reconciled["published_pet_friendly"] + reconciled["verified_no_pets"] \
            + reconciled["unresolved_or_held"] != census_total:
        raise WorkBrowserInputError("Dayton reconciliation does not close")

    identity_counts: Dict[str, int] = {}
    for hotel in census.values():
        identity_counts[hotel["identity_state"]] = \
            identity_counts.get(hotel["identity_state"], 0) + 1

    return OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("run_id", RUN_ID),
        ("as_of", AS_OF),
        ("reviewer_id", REVIEWER),
        ("market_id", MARKET),
        ("input_package", OrderedDict([
            ("path", "data/operator_evidence/dayton-founder-review-001/"
                     "incoming/work-browser-pass-001"),
            ("tracked", False),
            ("file_count", len(EXPECTED_FILES)),
            ("sha256", dict(input_hashes(directory))),
        ])),
        ("queue_baseline", OrderedDict(sorted(QUEUE_BASELINE.items()))),
        ("baseline_drift", OrderedDict([
            ("note",
             "The 90-row queue is the complement of a 33 published / 6 no-pets "
             "partition. PTF-DAYTON-CANDIDATE-PROMOTION-001 landed afterwards "
             "and took the market to 44 / 7, so twelve of the 90 rows describe "
             "properties already answered. They are reconciled as "
             "ALREADY_RESOLVED_BEFORE_THIS_PASS rather than re-adjudicated."),
            ("rows_already_published", sorted(
                i["slug"] for i in items
                if i["published_before"])),
            ("rows_already_excluded", sorted(
                i["slug"] for i in items if i["verified_no_pets_before"])),
        ])),
        ("evidence_determination", OrderedDict([
            ("artifact_class", ARTIFACT_CLASS),
            ("verdict", ARTIFACT_VERDICT),
            ("screenshots_declared_by_the_package", False),
            ("screenshot_tree_on_disk", False),
            ("accepted_for_publication", False),
            ("accepted_as_a_pointer_to_stored_captures", True),
            ("accepted_for_routing_proposals", True),
            ("transcribed_quotes_found_in_a_stored_capture",
             sum(1 for i in items
                 if i["transcription_corroborated_by_a_stored_capture"])),
        ])),
        ("best_western_structured_flag", OrderedDict([
            ("finding", BW_FLAG_FINDING),
            ("survey", best_western_pets_allowed_survey(
                load_captures(BW_SURVEY_DIRS))),
        ])),
        ("cross_market_findings", CROSS_MARKET_FINDINGS),
        ("reconciliation", reconciliation),
        ("outcome_counts", outcome_counts),
        ("market_reconciliation", reconciled),
        ("identity_states", OrderedDict(sorted(identity_counts.items()))),
        ("published_by_this_pass", [r["key"] for r in accepted]),
        ("verified_no_pets_by_this_pass", [r["normalized_name"] for r in exclusions]),
        ("routing_adjudication", [OrderedDict([
            ("slug", slug),
            ("canonical_name", census[slug]["canonical_name"]),
            ("decision", decision),
            ("routing_status", status),
            ("reason", reason),
            ("next_action", action),
        ]) for slug, (decision, status, reason, action)
            in ROUTING_ADJUDICATION.items()]),
        ("routing_accepted", sum(1 for d in ROUTING_ADJUDICATION.values()
                                 if d[0] == ACCEPTED)),
        ("routing_held", sum(1 for d in ROUTING_ADJUDICATION.values()
                             if d[0] == HELD)),
        ("routing_rejected", sum(1 for d in ROUTING_ADJUDICATION.values()
                                 if d[0] == REJECTED)),
        ("routing_records_written", [r["routing_id"] for r in routing_records]),
        ("items", items),
    ])


def _corroborated(row: Mapping, captures: Mapping) -> bool:
    """True when the transcribed wording is a literal substring of a
    hash-verified capture this repository already stores.

    This is the measurement that turns "the transcription cannot publish" from
    a dead end into a work list: it says which of the forty-one quotes the
    repository can already check, and therefore which of them a capture pass
    would not have to re-acquire.
    """
    quote = row["policy_text"].strip()
    if not quote:
        return False
    needle = _norm(quote)
    for cap in (capture_for(row["final_url"] or row["queued_url"], captures),
                captures.get("slug::" + row["slug"])):
        if cap and needle in cap["body"]:
            return True
    return False


def serialize(document: Mapping) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------- #
# Write.
# --------------------------------------------------------------------------- #

def write(document: Mapping = None, *, directory: Path = None) -> Dict:
    doc = document if document is not None else build(directory)
    census = load_census()
    captures = load_captures()
    observations = build_observations(census, captures)
    states = readiness_by_slug(observations)
    accepted, exclusions, _q = build_records(census, captures, states)
    rows = seed_rows(accepted, census)

    # The publication guard, on the identities about to publish.
    EX.assert_not_excluded_for_publication(
        [(r["name"], r["address"], r["postal_code"]) for r in rows])

    _write_lf(LEDGER_PATH, serialize(doc))

    facts_doc = _read_json(FACTS_PATH)
    have = {h["key"] for h in facts_doc["hotels"]}
    new_facts = [r for r in accepted if r["key"] not in have]
    facts_doc["hotels"].extend(new_facts)
    _write_lf(FACTS_PATH, json.dumps(facts_doc, indent=2, ensure_ascii=False) + "\n")

    exdoc = _read_json(EX.EXCLUSIONS_PATH)
    existing = {r["exclusion_id"] for r in exdoc["exclusions"]}
    new_exclusions = [r for r in exclusions if r["exclusion_id"] not in existing]
    exdoc["exclusions"].extend(new_exclusions)
    EX.validate(exdoc)
    _write_lf(EX.EXCLUSIONS_PATH, json.dumps(exdoc, indent=2, ensure_ascii=False) + "\n")

    with PRODUCTION_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        current = list(reader)
    have_rows = {(r["name"], r.get(MARKET_ID_FIELD, "")) for r in current}
    added = [r for r in rows if (r["name"], MARKET) not in have_rows]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in current + added:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    _write_lf(PRODUCTION_CSV, buf.getvalue())

    routing_doc = _read_json(ROUTING_PATH)
    before = len(routing_doc["routes"])
    known = {r["routing_id"] for r in routing_doc["routes"]}
    new_routes = [r for r in build_routing_records(
                      census, {x["slug"]: x for x in load_rows(directory)},
                      seed_keys([r["key"] for r in accepted]))
                  if r["routing_id"] not in known]
    routing_doc["routes"].extend(new_routes)
    routing_doc["count"] = len(routing_doc["routes"])
    batches = routing_doc.setdefault("source_batches", [])
    if RUN_ID not in batches:
        batches.append(RUN_ID)
    validate_authority(routing_doc)
    _write_lf(ROUTING_PATH, json.dumps(routing_doc, indent=1, ensure_ascii=False) + "\n")

    return {
        "ledger": str(LEDGER_PATH),
        "facts_added": len(new_facts),
        "exclusions_added": len(new_exclusions),
        "seed_rows_added": len(added),
        "routes_before": before,
        "routes_added": len(new_routes),
        "routes_after": len(routing_doc["routes"]),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not input_present():
        sys.stderr.write("input package absent: %s\n" % INPUT_DIR)
        return 2
    document = build()
    lines = [
        "%s -- %s" % (WORK_ORDER, MARKET),
        "  reconciled ............ %d / %d  (duplicates %d, omissions %d)"
        % (document["reconciliation"]["reconciled"], EXPECTED_QUEUE_SIZE,
           document["reconciliation"]["duplicates"],
           document["reconciliation"]["omissions"]),
        "  artifact class ........ %s" % document["evidence_determination"]["artifact_class"],
        "  quotes corroborated ... %d of %d by a stored capture"
        % (document["evidence_determination"]["transcribed_quotes_found_in_a_stored_capture"],
           EXPECTED_POLICY_WORDING_ROWS),
        "  routing ............... %d accepted / %d held / %d rejected"
        % (document["routing_accepted"], document["routing_held"],
           document["routing_rejected"]),
        "  published .............. %d  (+%d)"
        % (document["market_reconciliation"]["published_pet_friendly"],
           len(document["published_by_this_pass"])),
        "  verified no-pets ....... %d  (+%d)"
        % (document["market_reconciliation"]["verified_no_pets"],
           len(document["verified_no_pets_by_this_pass"])),
        "  unresolved or held ..... %d"
        % document["market_reconciliation"]["unresolved_or_held"],
    ]
    for name in OUTCOMES:
        lines.append("  %-46s %d" % (name, document["outcome_counts"][name]))
    sys.stdout.write("\n".join(lines) + "\n")

    if "--apply" in argv:
        result = write(document)
        sys.stdout.write(
            "wrote ledger; facts +%d, exclusions +%d, seed rows +%d, routes "
            "%d -> %d\n" % (result["facts_added"], result["exclusions_added"],
                            result["seed_rows_added"], result["routes_before"],
                            result["routes_after"]))
    else:
        sys.stdout.write("\nDry run. Pass --apply to write.\n")
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
