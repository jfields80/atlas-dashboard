"""PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 -- adjudicate the Work-browser pass.

The founder ran the 135-property Cleveland review queue through a ChatGPT Work
browser and handed back 27 files: twelve batch review CSVs, twelve batch
manifests, a rolled-up review CSV, a rolled-up manifest, and a screenshot
queue. This module is the integrator's side of that handback. It re-derives
every count rather than trusting the manifests, adjudicates all 135 properties
into mutually exclusive outcomes, and writes ONE tracked ledger.

WHY NOTHING IN THIS BATCH PUBLISHES A PET POLICY
------------------------------------------------
The package is a TRANSCRIPTION. For each property it carries the operator's
typed record of what the browser displayed: a hotel name, an address, a phone,
and the pet wording as prose in a spreadsheet cell. What it does not carry --
anywhere, for any of the 135 -- is an artifact of the surface those words were
read from. There is no HTML, no DOM snapshot, and no screenshot: all 135
directories under ``screenshots/`` exist and all 135 are empty.

Atlas requires such an artifact, and it requires it in three separate places,
each of which was checked against this package:

  * ``hotel_policy_facts_*.json``. Every one of the 129 records published across
    Columbus, Cleveland and Dayton carries a ``sha256:`` provenance hash, and
    ``test_export_authority_guard`` asserts exactly that. The three accepted
    routes are ``machine_review.approval_hash``,
    ``attended_capture.html_sha256`` and ``manual_evidence.policy_source_sha256``
    -- and in the manual-evidence route (PTF-COLUMBUS-HYATT-002) the hash is of
    an operator screenshot OF THE PROPERTY'S OWN PAGE, listed in
    ``policy_artifacts``. The artifact is a depiction of the source. A hash of a
    spreadsheet is a hash of the transcription, which proves the typing has not
    changed and says nothing about what the page said.
  * ``hotel_exclusions.json``. ``source_hash`` is a REQUIRED field for every
    record, and every integrator that has ever written one
    (``integrate_cleveland_authority``, ``integrate_dayton_authority``,
    ``integrate_dayton_recovery_002``) sets it from the capture's
    ``html_sha256``. A refusal is guarded at the same bar as a permission, so
    the sixteen no-pets findings in this batch are held exactly as the
    seventy-one affirmative ones are.
  * ``policy_membrane`` M9 -- no field without a quote -- is enforceable only
    against something. Every prior integration asserts each quote is a literal
    substring of its own capture before the fact it carries may publish. With
    no capture there is nothing to assert against, and the check becomes a
    comment.

So this batch produces an evidence-completion queue, not a publication. That is
the outcome the work order anticipated ("if Atlas requires a screenshot or
captured page and none exists, do not publish from the transcription alone"),
and it is reached here by consulting the contracts rather than by assuming it.

Note that a quote's CONTENT was never the obstacle. Fifty-five of the eighty
visible-policy rows are marketing copy ("our pet-friendly hotel ...") that would
land on ``readiness.POLICY_PARTIAL`` even with a perfect capture -- the same
finding ``integrate_cleveland_capture_003`` recorded for three Wyndham
properties. Twenty-five state a real fee, weight or count. Both groups are held
for the same reason, and the ledger records which is which so a later capture
pass can start with the twenty-five that would publish.

THE ONE THING THAT DOES CHANGE
------------------------------
One of the fifteen proposed routing corrections is accepted. Sonesta rebranded
ES Suites Cleveland Airport to Simply Suites, and the URL on record is the dead
ES Suites path. This was not accepted on the transcription's word: the recorded
URL was fetched and 301-redirects to the proposed one, and the page's own
JSON-LD carries ``"streetAddress":"17525 Rosbough Drive"``,
``"postalCode":"44130"``, ``"telephone":"(440) 234-6688"`` and
``"name":"Sonesta Simply Suites Cleveland Airport"`` -- three strong identity
keys agreeing with the census, read first-party from the destination itself.

The other fourteen are rejected, and the reasons are worth stating because
eleven of them are not really routing proposals at all: six propose the URL
already on record with a trailing slash or a fragment added; three of those six
rendered ``502 Bad Gateway``; two propose a URL carrying a Cloudflare challenge
token or a session date parameter, which are per-session artifacts that must
never enter authority; two propose a brand SEARCH or CITY page instead of a
property page; and three propose the address of a different business that
happens to share the hotel's campus. See ``ROUTING_ADJUDICATION``.

A routing record is not publication -- nothing in the publication path reads
``identity_routing.json`` -- so this change cannot move a count, a route or a
byte of the built site. What it does is point the next capture pass at a page
that exists.

Run:  python -m scripts.pettripfinder.integrate_cleveland_work_browser_001 [--apply]
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.hotel_exclusions import address_key            # noqa: E402
from scripts.pettripfinder.identity_routing import (                      # noqa: E402
    ROUTING_CONFIRMED,
    BINDING_PAGE_RENDERED,
    registrable_domain,
    validate_record,
)

MARKET = "cleveland-akron-canton-oh"
RUN_ID = "cleveland-work-browser-pass-001"
WORK_ORDER = "PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001"
AS_OF = "2026-08-12"
REVIEWER = "jfields80"
SCHEMA = "ptf-cleveland-work-browser-adjudication/1.0"

#: The operator package. Untracked by design -- ``data/`` is gitignored, and
#: research residue is not authority. Every consumer of this module must treat
#: its absence as a skip, never as an empty result.
INPUT_DIR = (_REPO_ROOT / "data" / "operator_evidence" / "cleveland-founder-review-001"
             / "incoming" / "work-browser-pass-001")
SCREENSHOT_DIR = (_REPO_ROOT / "data" / "operator_evidence"
                  / "cleveland-founder-review-001" / "screenshots")

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / ("%s.json" % MARKET))
ROUTING_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                / "identity_routing.json")
FACTS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
              / ("hotel_policy_facts_%s.json" % MARKET))
EXCLUSIONS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                   / "hotel_exclusions.json")
LEDGER_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "cleveland_work_browser_pass_001.json")

#: Exactly what the package must contain. A missing or extra file is a gate
#: failure, not a warning -- a partial handback reconciled against a 135-row
#: queue would silently under-count.
EXPECTED_FILES: Tuple[str, ...] = tuple(
    ["batch-%03d-review.csv" % i for i in range(1, 13)]
    + ["batch-%03d-manifest.json" % i for i in range(1, 13)]
    + ["work-browser-pass-001-review.csv",
       "work-browser-pass-001-manifest.json",
       "work-browser-screenshot-queue.csv"])

EXPECTED_QUEUE_SIZE = 135

#: The partition the work order states as expected input. Verified, not trusted:
#: ``reconcile()`` recomputes it from the batch CSVs and refuses a mismatch.
EXPECTED_PARTITION = {
    "visible_policy": 80,
    "identity_only": 28,
    "routing_correction_proposed": 15,
    "blocked_or_incomplete": 12,
}

# --------------------------------------------------------------------------- #
# The two CSV shapes. Batch 2 predates the others (it is the earlier Hyatt
# pass) and uses its own column names; normalising here keeps every rule below
# written once.
# --------------------------------------------------------------------------- #

_COLUMNS_STANDARD = {
    "slug": "slug", "queued_name": "queued property name", "queued_url": "queued URL",
    "final_name": "final displayed hotel name", "final_url": "final URL",
    "address": "displayed address", "phone": "displayed phone",
    "property_code": "visibly displayed property code",
    "policy_text": "exact visible pet-policy wording",
    "supported": "supported facts", "withheld": "withheld facts",
    "contradictions": "contradictions or warnings",
    "classification": "browser result classification",
    "routing_status": "routing-correction status",
    "replacement_url": "proposed replacement URL",
    "identity_keys": "identity keys supporting any proposed correction",
    "screenshot_ready": "screenshot-ready",
    "next_action": "exactly one next action",
}

_COLUMNS_BATCH_2 = {
    "slug": "slug", "queued_name": "queue_property_name", "queued_url": "queue_url",
    "final_name": "exact_displayed_hotel_name",
    "final_url": "official_evidence_final_url",
    "address": "exact_displayed_address", "phone": "exact_displayed_phone",
    "property_code": "exact_displayed_property_code",
    "policy_text": "exact_visible_pet_policy_text",
    "supported": "supported_facts", "withheld": "withheld_facts",
    "contradictions": "contradictions",
    "classification": "final_classification",
    "routing_status": "routing_correction_status",
    "replacement_url": "routing_replacement_proposed",
    "identity_keys": "routing_identity_keys",
    "screenshot_ready": "screenshot_status",
    "next_action": None,
}

#: Browser classifications that mean "the page rendered and stated something
#: about pets". Three spellings, because batch 2 used its own.
VISIBLE_POLICY_CLASSIFICATIONS = frozenset({
    "BROWSER_VERIFIED_POLICY_VISIBLE",
    "EVIDENCE_SUCCESS_POLICY_VISIBLE",
    "EVIDENCE_SUCCESS_OFFICIAL_ROUTE_RECOVERED",
})
IDENTITY_ONLY_CLASSIFICATION = "BROWSER_IDENTITY_ONLY_POLICY_NOT_VISIBLE"
ROUTING_CLASSIFICATION = "ROUTING_CORRECTION_PROPOSED"
BLOCKED_CLASSIFICATIONS = frozenset({
    "CAPTCHA_OR_ANTI_BOT", "HTTP_404", "JS_RENDERED_BLANK_CONTENT",
    "POLICY_MODAL_BLANK",
})


class WorkBrowserInputError(RuntimeError):
    """The handback does not reconcile against the queue it claims to answer."""


# --------------------------------------------------------------------------- #
# Outcomes. Closed, mutually exclusive, and every property lands in exactly one.
# --------------------------------------------------------------------------- #

OUT_PUBLISHED = "ACCEPTED_AND_PUBLISHED_PET_FRIENDLY"
OUT_VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
OUT_ROUTING_CORRECTED = "IDENTITY_OR_ROUTING_CORRECTED_POLICY_UNRESOLVED"
OUT_EVIDENCE_CANDIDATE = "EVIDENCE_CANDIDATE_AWAITING_ACCEPTED_ARTIFACT"
OUT_IDENTITY_ONLY = "IDENTITY_ONLY"
OUT_ACCESS_BLOCKED = "ACCESS_BLOCKED"
OUT_CONTRADICTION = "CONTRADICTION"
OUT_SURFACE_GAP = "SELECTOR_OR_SURFACE_GAP"
OUT_MANUAL = "MANUAL_VERIFICATION_REQUIRED"
OUT_OTHER = "OTHER_UNRESOLVED"

OUTCOMES = (OUT_PUBLISHED, OUT_VERIFIED_NO_PETS, OUT_ROUTING_CORRECTED,
            OUT_EVIDENCE_CANDIDATE, OUT_IDENTITY_ONLY, OUT_ACCESS_BLOCKED,
            OUT_CONTRADICTION, OUT_SURFACE_GAP, OUT_MANUAL, OUT_OTHER)

#: Outcomes that assert something about the property's pet policy. This batch
#: reaches none of them, and ``build()`` proves that rather than stating it.
RESOLVING_OUTCOMES = frozenset({OUT_PUBLISHED, OUT_VERIFIED_NO_PETS})


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


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def input_hashes(directory: Path = None) -> "OrderedDict[str, str]":
    """The 27 files and their hashes, in a fixed order.

    Hashing is preservation, not acceptance: it records precisely which
    transcription was adjudicated, so a later screenshot pass can be compared
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


def _read_batch(path: Path, batch_number: int) -> List[Dict[str, str]]:
    columns = _COLUMNS_BATCH_2 if batch_number == 2 else _COLUMNS_STANDARD
    rows: List[Dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            row = {key: str(raw.get(src, "") or "").strip() if src else ""
                   for key, src in columns.items()}
            row["batch"] = batch_number
            rows.append(row)
    return rows


def load_rows(directory: Path = None) -> List[Dict[str, str]]:
    """All 135 reviewed rows, one per property, from the twelve batch CSVs.

    The rolled-up ``work-browser-pass-001-review.csv`` carries only 131: its own
    manifest declares ``batch_2_not_repeated``, because batch 2 was reviewed in
    an earlier session and was deliberately not re-run. Reconciling against the
    roll-up alone would drop four properties silently, so the batches are the
    source and the roll-up is checked against them.
    """
    base = Path(directory) if directory else INPUT_DIR
    rows: List[Dict[str, str]] = []
    for number in range(1, 13):
        rows.extend(_read_batch(base / ("batch-%03d-review.csv" % number), number))
    return rows


def load_rollup_slugs(directory: Path = None) -> List[str]:
    base = Path(directory) if directory else INPUT_DIR
    with (base / "work-browser-pass-001-review.csv").open(
            newline="", encoding="utf-8-sig") as handle:
        return [str(r.get("slug", "")).strip() for r in csv.DictReader(handle)]


# --------------------------------------------------------------------------- #
# Reconciliation.
# --------------------------------------------------------------------------- #

def partition_of(classification: str) -> str:
    if classification in VISIBLE_POLICY_CLASSIFICATIONS:
        return "visible_policy"
    if classification == IDENTITY_ONLY_CLASSIFICATION:
        return "identity_only"
    if classification == ROUTING_CLASSIFICATION:
        return "routing_correction_proposed"
    if classification in BLOCKED_CLASSIFICATIONS:
        return "blocked_or_incomplete"
    raise WorkBrowserInputError("unknown browser classification %r" % classification)


def reconcile(rows: Sequence[Mapping], rollup_slugs: Sequence[str],
              census_slugs: Sequence[str]) -> Dict:
    """Every property accounted for exactly once, against the queue and census.

    Refuses on any of: a row count other than 135, a duplicate slug, a slug the
    Cleveland census does not know, a roll-up slug absent from the batches, or a
    partition that does not equal ``EXPECTED_PARTITION``.
    """
    slugs = [r["slug"] for r in rows]
    duplicates = sorted({s for s in slugs if slugs.count(s) > 1})
    if duplicates:
        raise WorkBrowserInputError("duplicate reconciliations: %s" % duplicates)
    if len(slugs) != EXPECTED_QUEUE_SIZE:
        raise WorkBrowserInputError(
            "expected %d reviewed properties, found %d" % (EXPECTED_QUEUE_SIZE, len(slugs)))

    known = set(census_slugs)
    unbound = sorted(s for s in slugs if s not in known)
    if unbound:
        raise WorkBrowserInputError(
            "row(s) bind to no %s census identity: %s" % (MARKET, unbound))

    missing_from_batches = sorted(set(rollup_slugs) - set(slugs))
    if missing_from_batches:
        raise WorkBrowserInputError(
            "roll-up names slug(s) no batch reviewed: %s" % missing_from_batches)

    counts: Dict[str, int] = {name: 0 for name in EXPECTED_PARTITION}
    for row in rows:
        counts[partition_of(row["classification"])] += 1
    if counts != EXPECTED_PARTITION:
        raise WorkBrowserInputError(
            "partition mismatch: expected %s, derived %s" % (EXPECTED_PARTITION, counts))

    return {
        "queued": EXPECTED_QUEUE_SIZE,
        "reconciled": len(slugs),
        "duplicates": 0,
        "omissions": 0,
        "partition": dict(counts),
        "rollup_rows": len(rollup_slugs),
        "batch_2_not_in_rollup": sorted(set(slugs) - set(rollup_slugs)),
    }


# --------------------------------------------------------------------------- #
# The evidence question, asked once and answered the same way for all 135.
# --------------------------------------------------------------------------- #

ARTIFACT_CLASS = "OPERATOR_TRANSCRIBED_BROWSER_REVIEW"

ARTIFACT_VERDICT = (
    "NOT_A_PUBLICATION_GRADE_ARTIFACT_CLASS: the package carries the operator's "
    "typed record of what a browser displayed and no artifact of the surface it "
    "was read from. hotel_policy_facts requires a sha256 of a captured page or "
    "of an operator screenshot of that page (machine_review.approval_hash, "
    "attended_capture.html_sha256, manual_evidence.policy_source_sha256); "
    "hotel_exclusions requires source_hash, which every integrator sets from a "
    "capture's html_sha256; and policy_membrane M9 can only be enforced against "
    "a stored surface. Hashing the CSV binds the transcription, not the page.")


def screenshot_inventory(directory: Path = None) -> Dict[str, int]:
    """What the screenshot tree actually holds.

    The work order asked that Batch 2 Hyatt screenshots be bound "where
    present". They are not present: 135 directories exist and every one is
    empty. The only operator screenshots in this repository are the eleven under
    ``hyatt-batch-001``, and all eleven are already bound to Columbus records.
    """
    base = Path(directory) if directory else SCREENSHOT_DIR
    if not base.is_dir():
        return {"directories": 0, "files": 0}
    directories = [p for p in base.iterdir() if p.is_dir()]
    files = sum(1 for p in base.rglob("*") if p.is_file())
    return {"directories": len(directories), "files": files}


_NEGATIVE = re.compile(
    r"pets\s+allowed:\s*no|no\s+pets\s+allowed|pets\s+not\s+allowed"
    r"|pets\s+are\s+not\s+(?:allowed|permitted)|or\s+pets\s+allowed", re.I)
_AFFIRMATIVE = re.compile(
    r"pets\s+allowed:\s*yes|pets\s+are\s+allowed|pets?\s+welcome|pets\s+are\s+welcome"
    r"|we\s+are\s+pet\s+friendly|pet[-\s]friendly|welcomes?\s+your|dogs?\s+are\s+allowed"
    r"|pets\s+are\s+permitted|your\s+pets\s+are\s+welcome", re.I)
#: A page that renders only the FAQ question ("Can I bring my pet to X?") with
#: no answer beneath it. IHG's accordion is client-side; the question is markup
#: and the answer never arrives. Six rows in this batch are exactly this, and
#: counting them as "policy visible" would be counting the question as its own
#: answer.
_QUESTION_ONLY = re.compile(r"^\s*can i bring my pet to [^?]*\?\s*$", re.I)

#: Wording that states a term a reader would act on. Used only to rank the
#: evidence-completion queue: a capture of one of these publishes a real policy,
#: while a capture of marketing copy lands on POLICY_PARTIAL either way.
_STRUCTURED = (
    re.compile(r"\$\s?\d|\bfee of\b|\bper night\b|\bper stay\b|\bper pet\b", re.I),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:lb|lbs|pound)|weight limit", re.I),
    re.compile(r"maximum (?:of )?\w+ (?:pets?|dogs?)|maximum number of pets"
               r"|a maximum of \d+", re.I),
)


def policy_shape(text: str) -> str:
    """What the transcribed wording says, independent of whether it may publish.

    Returns one of ``AFFIRMATIVE_STRUCTURED``, ``AFFIRMATIVE_MARKETING_ONLY``,
    ``NEGATIVE``, ``CONTRADICTORY``, ``QUESTION_ONLY``, ``NONE``.
    """
    body = (text or "").strip()
    if not body:
        return "NONE"
    if _QUESTION_ONLY.match(body):
        return "QUESTION_ONLY"
    negative = bool(_NEGATIVE.search(body))
    affirmative = bool(_AFFIRMATIVE.search(body))
    if negative and affirmative:
        return "CONTRADICTORY"
    if negative:
        return "NEGATIVE"
    if not affirmative:
        return "NONE"
    return ("AFFIRMATIVE_STRUCTURED"
            if any(p.search(body) for p in _STRUCTURED)
            else "AFFIRMATIVE_MARKETING_ONLY")


# --------------------------------------------------------------------------- #
# Routing adjudication. Hand-authored, one entry per proposal, and every
# rejection names the criterion it failed rather than a mood.
# --------------------------------------------------------------------------- #

ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"

#: slug -> (decision, reason, one next action)
ROUTING_ADJUDICATION: "OrderedDict[str, Tuple[str, str, str]]" = OrderedDict([
    ("sonesta-es-suites-cleveland-airport", (
        ACCEPTED,
        "First-party and self-proving: the URL on record 301-redirects to the "
        "proposed one, and the destination's own JSON-LD carries "
        "streetAddress '17525 Rosbough Drive', postalCode '44130', telephone "
        "'(440) 234-6688' and name 'Sonesta Simply Suites Cleveland Airport'. "
        "Street key (17525|rosbough|44130) and phone both equal the census; the "
        "name is the same property under Sonesta's ES Suites -> Simply Suites "
        "rebrand. Same registrable domain as the record, market boundary agrees "
        "(Middleburg Heights is Cleveland-Akron-Canton), and no other identity "
        "owns the URL or a property code.",
        "Queue the corrected URL for a policy capture; the route is now live "
        "but the pet policy is still unobserved.")),

    ("extended-stay-america-premier-suites", (
        REJECTED,
        "The record's URL is provably wrong -- it is a Hyatt route for an "
        "Extended Stay America property, and it now lands on Hyatt's generic "
        "reservations page -- but the replacement rendered NOTHING: the browser "
        "was blocked for automated activity. Every identity key offered comes "
        "from a search-engine index result, not from the destination, so no key "
        "agrees between the proposed page and the census. First-party test "
        "passes; two-strong-keys test fails.",
        "Recover the Extended Stay America Independence property URL from a "
        "first-party surface (brand locator or CVB anchor) and re-propose.")),

    ("studio-6-extended-stay-hotel-mentor", (
        REJECTED,
        "Street key agrees (7677|reynolds|44060) but the phone does not "
        "(census 440-946-0749, page 440-299-8653) and the displayed brand is "
        "Suburban Studios, not Studio 6. One key of three. Separately, the "
        "'replacement' is the recorded URL plus a ?checkOutDate=2026-08-18 "
        "session parameter, which is a per-visit artifact and may never enter "
        "authority.",
        "Refresh the census identity for this address: the property appears to "
        "have rebranded Studio 6 -> Suburban Studios, so the name and phone on "
        "record are stale.")),

    ("days-inn-richfield", (
        REJECTED,
        "The proposal is a brand SEARCH page (/hotels/richfield-ohio?brand_id=DI) "
        "whose displayed title is 'Search Results'. A search page is not an "
        "official property endpoint and binds no identity.",
        "Re-resolve the Days Inn Richfield property page from the Wyndham "
        "brand locator and re-propose.")),

    ("comfort-suites-hartville", (
        REJECTED,
        "Two independent failures. The recorded URL is hartvillekitchen.com, a "
        "restaurant, so the route was already wrong; and the replacement is that "
        "same URL carrying a Cloudflare __cf_chl_rt_tk challenge token, with "
        "displayed title 'Just a moment...'. A challenge token is a per-session "
        "artifact and the interstitial binds no identity.",
        "Recover the Comfort Suites Hartville property URL from the Choice "
        "brand locator; the restaurant domain on record is a mis-binding.")),

    ("crowne-plaza-cleveland-airport", (
        REJECTED,
        "The replacement is the recorded URL with a trailing slash -- the same "
        "resource -- and it rendered 502 Bad Gateway. No correction is proposed "
        "and no identity was displayed.",
        "Recover a working Crowne Plaza Cleveland Airport endpoint from the IHG "
        "brand locator; crowneplazacle.com is returning 502.")),

    ("embassy-suites-by-hilton-akron-canton-airport", (
        REJECTED,
        "The replacement equals the recorded URL. That URL is "
        "luggageroomspeakeasy.com, which displays 'The Luggage Room' -- the bar "
        "on the hotel's campus. Address and phone agree because the bar shares "
        "the hotel's building; the NAME does not, which is precisely the "
        "same-campus case M10 refuses to let an address override.",
        "Replace the routing URL with the Hilton property page for Embassy "
        "Suites Akron Canton Airport; the record currently points at the "
        "on-site bar.")),

    ("highlander-inn", (
        REJECTED,
        "The replacement is the recorded URL with a trailing slash and it "
        "rendered 502 Bad Gateway. No correction, no identity.",
        "Recover a working Highlander Inn endpoint or record the property as "
        "having no reachable official URL.")),

    ("intercontinental-suites-hotel-cleveland", (
        REJECTED,
        "The proposed domain change (intercontinentalsuitescleveland.com -> "
        "icsuitescleveland.com) is plausible, but the destination displayed "
        "'Attention Required! | Cloudflare'. A challenge page states no name, "
        "no address and no phone, so zero identity keys agree.",
        "Re-attempt icsuitescleveland.com in an attended browser and re-propose "
        "with the page's own address and phone.")),

    ("sonesta-es-suites-cleveland-westlake", (
        REJECTED,
        "The proposal is Sonesta's CITY page for Westlake ('Find & Book Hotels "
        "in Westlake, Ohio'), not a property page. It displayed no address and "
        "no phone, and it would route a capture at a list of hotels rather than "
        "at this one.",
        "Resolve the Sonesta property page for 30100 Clemens Rd, Westlake -- "
        "most likely the Simply Suites rebrand path, as at Cleveland Airport -- "
        "and re-propose.")),

    ("springhill-suites-solon", (
        REJECTED,
        "The replacement is the recorded URL with a trailing slash and it "
        "rendered 502 Bad Gateway.",
        "Replace the dead springhillsolon.com vanity domain with the Marriott "
        "property page for SpringHill Suites Solon.")),

    ("the-bertram-hotel-conference-center", (
        REJECTED,
        "Not a correction. The proposal differs from the record only by dropping "
        "the 'www.' label; it is the same registrable domain and the same "
        "resource. The page did corroborate the record -- displayed address "
        "'600 North Aurora Road, Aurora, OH 44202-7107' and phone (330) 995-0200 "
        "both agree with the census -- so the routing on file is confirmed, not "
        "changed.",
        "No routing action; queue the existing URL for a policy capture, since "
        "the page rendered but stated no pet policy.")),

    ("the-bertram-inn-at-glenmoor", (
        REJECTED,
        "The proposal routes further from the hotel, not closer: "
        "thespaatglenmoor.org displays 'the-spa-at-glenmoor' and a different "
        "phone (330-966-3524 against the census's 330-966-3600). The spa is a "
        "separate business on the Glenmoor campus.",
        "Resolve the lodging page for The Bertram Inn at Glenmoor on "
        "glenmoorcc.com; both the recorded /Spa path and the proposal point at "
        "the spa.")),

    ("the-rowley-inn", (
        REJECTED,
        "The replacement equals the recorded URL, which displays 'Tremont "
        "Restaurant - Tremont Bar'. The phone agrees, but the page presents a "
        "restaurant and states no lodging identity, and no street address was "
        "displayed.",
        "Determine whether The Rowley Inn is lodging inventory at all; if it is "
        "not, it belongs in hotel_exclusions as OUT_OF_CURRENT_CATEGORY on "
        "captured evidence, not in the capture queue.")),

    ("economy-inn", (
        REJECTED,
        "The proposal is the recorded URL with a '#/' fragment appended. A "
        "fragment is not a distinct resource, so there is nothing to correct; "
        "the displayed title was a generic booking banner rather than the "
        "property's name.",
        "No routing action; queue the existing URL for an attended capture, "
        "since the site renders its content client-side.")),
])


# --------------------------------------------------------------------------- #
# Per-property outcome. Ordered so the first matching rule wins, strongest
# statement first.
# --------------------------------------------------------------------------- #

#: Routing rows whose failure was the destination refusing to render at all.
_ROUTING_BLOCKED = frozenset({
    "extended-stay-america-premier-suites", "comfort-suites-hartville",
    "intercontinental-suites-hotel-cleveland",
})
#: Routing rows whose recorded URL resolves to a DIFFERENT business.
_ROUTING_WRONG_ENTITY = frozenset({
    "embassy-suites-by-hilton-akron-canton-airport", "the-bertram-inn-at-glenmoor",
    "the-rowley-inn",
})

#: A property in the queue that is not lodging. Its own page describes a dog
#: daycare and pet spa. PTF-CLEVELAND-MARKET-FACTORY-001 removed five such rows
#: and this one survived; recording it here is the evidence that closes it.
_NON_LODGING = frozenset({"inn-the-doghouse"})


def outcome_for(row: Mapping) -> Tuple[str, str, str]:
    """(outcome, reason_code, next_action) for one reviewed property."""
    slug = row["slug"]
    classification = row["classification"]

    if classification == ROUTING_CLASSIFICATION:
        decision, _reason, action = ROUTING_ADJUDICATION[slug]
        if decision == ACCEPTED:
            return OUT_ROUTING_CORRECTED, "ROUTING_CORRECTION_ACCEPTED", action
        if slug in _ROUTING_BLOCKED:
            return OUT_ACCESS_BLOCKED, "ROUTING_DESTINATION_REFUSED_TO_RENDER", action
        if slug in _ROUTING_WRONG_ENTITY:
            return OUT_MANUAL, "ROUTED_URL_RESOLVES_TO_A_DIFFERENT_BUSINESS", action
        return OUT_OTHER, "ROUTING_CORRECTION_REJECTED_NO_VALID_REPLACEMENT", action

    if classification == IDENTITY_ONLY_CLASSIFICATION:
        return (OUT_IDENTITY_ONLY, "PAGE_RENDERED_NO_PET_POLICY_STATED",
                "Capture the property's pet-policy surface (accordion, modal or "
                "amenities page) that the overview page does not render.")

    if classification == "CAPTCHA_OR_ANTI_BOT":
        return (OUT_ACCESS_BLOCKED, "ANTI_BOT_CHALLENGE",
                "Re-attempt in an attended browser under capture_automation "
                "doctrine pacing; no challenge may be solved programmatically.")
    if classification == "HTTP_404":
        # One of the four 404 rows is internally inconsistent: it reports
        # HTTP_404 and, in the same row, a fully rendered Marriott property
        # page -- correct title, street address, phone, a "Pets Not Allowed"
        # block, and screenshot-ready=yes. A 404 produces none of that. Neither
        # half is silently preferred: believing the classification discards a
        # transcribed refusal, and believing the transcription publishes off a
        # page the reviewer said was missing. It is recorded as the
        # contradiction it is.
        if row["policy_text"].strip() and row["address"].strip():
            return (OUT_MANUAL, "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION",
                    "Re-fetch this URL and record which half is true: the row "
                    "reports HTTP_404 while transcribing a rendered property "
                    "page with address, phone and a pet-policy block.")
        return (OUT_MANUAL, "OFFICIAL_URL_RETURNS_404",
                "Re-resolve this property's official URL from a first-party "
                "surface; the URL on record is dead.")
    if classification in ("JS_RENDERED_BLANK_CONTENT", "POLICY_MODAL_BLANK"):
        return (OUT_SURFACE_GAP, classification,
                "Capture with the policy surface expanded: the content is "
                "client-side and never entered the served markup.")

    # --- the eighty that rendered something about pets --------------------- #
    shape = policy_shape(row["policy_text"])
    if slug in _NON_LODGING:
        return (OUT_MANUAL, "QUEUED_IDENTITY_IS_NOT_LODGING",
                "Reclassify Inn the Doghouse out of the hotel category on its "
                "own captured page (a dog daycare and pet spa), via "
                "hotel_exclusions OUT_OF_CURRENT_CATEGORY.")
    if shape == "QUESTION_ONLY":
        return (OUT_SURFACE_GAP, "FAQ_QUESTION_RENDERED_WITHOUT_ITS_ANSWER",
                "Capture with the IHG pet-policy accordion expanded; the served "
                "markup carries the question and never the answer.")
    if shape == "CONTRADICTORY":
        return (OUT_CONTRADICTION, "PAGE_STATES_BOTH_PET_FRIENDLY_AND_NO_PETS",
                "Capture both conflicting surfaces so approval_resolution can "
                "adjudicate; this layer never selects a winner (M8).")
    if shape == "NEGATIVE":
        return (OUT_EVIDENCE_CANDIDATE, "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT",
                "Capture or screenshot the refusal sentence on the property's "
                "own page; hotel_exclusions requires source_hash and the "
                "transcription supplies none.")
    if shape in ("AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_MARKETING_ONLY"):
        return (OUT_EVIDENCE_CANDIDATE, "AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT",
                "Capture or screenshot the pet-policy block on the property's "
                "own page; every publication route requires a sha256 of the "
                "page and the transcription supplies none.")
    return (OUT_EVIDENCE_CANDIDATE, "PET_WORDING_TRANSCRIBED_ESTABLISHES_NOTHING",
            "Capture the property's pet-policy surface; the transcribed wording "
            "neither permits nor refuses pets.")


# --------------------------------------------------------------------------- #
# The accepted routing correction, as a change to the existing record.
# --------------------------------------------------------------------------- #

ACCEPTED_ROUTE_SLUG = "sonesta-es-suites-cleveland-airport"
ACCEPTED_ROUTE_ID = "route-cleveland-akron-canton-oh-sonesta-es-suites-cleveland-airport"
ACCEPTED_ROUTE_URL = ("https://www.sonesta.com/sonesta-simply-suites/oh/"
                      "middleburg-heights/sonesta-simply-suites-cleveland-airport")
#: sha256 of the destination as fetched on 2026-08-12 while verifying the
#: redirect and the JSON-LD identity keys. Recorded as provenance for the
#: BINDING decision only. It is NOT policy evidence and no pet fact is read
#: from it: routing says where a property speaks, never what it said.
ACCEPTED_ROUTE_HTML_SHA256 = (
    "sha256:47c4b170c23462f3345977df5021c66fe2841d4e4c4c81b477e2d7fadd5314a1")

ACCEPTED_ROUTE_SIGNALS = (
    "redirect=recorded ES Suites URL 301s to this Simply Suites URL",
    "jsonld_streetAddress=17525 Rosbough Drive",
    "jsonld_postalCode=44130",
    "jsonld_telephone=(440) 234-6688",
    "jsonld_name=Sonesta Simply Suites Cleveland Airport",
)


def apply_routing_correction(document: Dict) -> Tuple[Dict, Dict]:
    """Return (updated document, before/after summary) for the one accepted route.

    Rewrites exactly one record in place and revalidates it against the frozen
    ``ptf-identity-routing/1.0`` contract. Every other record is untouched, and
    the caller compares counts before and after.
    """
    routes = document["routes"]
    matches = [r for r in routes if r.get("routing_id") == ACCEPTED_ROUTE_ID]
    if len(matches) != 1:
        raise WorkBrowserInputError(
            "expected exactly one routing record %r, found %d"
            % (ACCEPTED_ROUTE_ID, len(matches)))
    record = matches[0]
    before = dict(record)

    record["official_property_url"] = ACCEPTED_ROUTE_URL
    record["official_domain"] = registrable_domain(ACCEPTED_ROUTE_URL)
    record["binding_method"] = BINDING_PAGE_RENDERED
    record["binding_sources"] = [
        "%s (fetched %s during %s; the recorded ES Suites URL 301-redirects "
        "here) html_sha256=%s" % (ACCEPTED_ROUTE_URL, AS_OF, WORK_ORDER,
                                  ACCEPTED_ROUTE_HTML_SHA256),
    ]
    record["identity_signals_matched"] = list(ACCEPTED_ROUTE_SIGNALS)
    record["observed_at"] = AS_OF
    record["verified_at"] = AS_OF
    record["status"] = ROUTING_CONFIRMED
    record["notes"] = (
        "%s: Sonesta rebranded this property from ES Suites to Simply Suites and "
        "the ES Suites path on record is superseded. Accepted on first-party "
        "proof read from the destination itself -- the redirect plus the page's "
        "own JSON-LD name, street address, postal code and telephone -- not on "
        "the operator transcription that proposed it. Identity remains the "
        "census's; the URL supplies only where to look, and no pet fact is "
        "carried or implied." % WORK_ORDER)

    validate_record(record)
    batches = document.setdefault("source_batches", [])
    if RUN_ID not in batches:
        batches.append(RUN_ID)
    document["count"] = len(routes)
    return document, {
        "routing_id": ACCEPTED_ROUTE_ID,
        "before_url": before["official_property_url"],
        "after_url": record["official_property_url"],
        "before_binding_method": before["binding_method"],
        "after_binding_method": record["binding_method"],
    }


# --------------------------------------------------------------------------- #
# Build.
# --------------------------------------------------------------------------- #

def _json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(directory: Path = None) -> Dict:
    """The whole adjudication, derived. Nothing below is typed twice."""
    rows = load_rows(directory)
    census = _json(CENSUS_PATH)
    census_by_slug = {h["slug"]: h for h in census["hotels"]}
    reconciliation = reconcile(rows, load_rollup_slugs(directory),
                               list(census_by_slug))

    facts = _json(FACTS_PATH)
    published_keys = {h["key"] for h in facts["hotels"]}
    exclusions = _json(EXCLUSIONS_PATH)
    exclusion_records = (exclusions["exclusions"] if isinstance(exclusions, dict)
                         else exclusions)
    cleveland_exclusions = [r for r in exclusion_records
                            if r.get("market_id") == MARKET]

    items: List[Dict] = []
    for row in sorted(rows, key=lambda r: r["slug"]):
        identity = census_by_slug[row["slug"]]
        outcome, reason, action = outcome_for(row)
        shape = policy_shape(row["policy_text"])
        page_address = re.sub(r",.*", "", row["address"] or "")
        items.append(OrderedDict([
            ("slug", row["slug"]),
            ("canonical_name", identity["canonical_name"]),
            ("normalized_name", identity["normalized_name"]),
            ("market_id", MARKET),
            ("batch", row["batch"]),
            ("browser_classification", row["classification"]),
            ("partition", partition_of(row["classification"])),
            ("outcome", outcome),
            ("reason_code", reason),
            ("next_action", action),
            ("policy_wording_shape", shape),
            ("transcribed_policy_wording", row["policy_text"]),
            ("source_url", row["final_url"] or row["queued_url"]),
            ("displayed_property_code", row["property_code"]),
            ("identity_check", OrderedDict([
                ("census_street_key", address_key(identity["address"],
                                                  identity["postal_code"])),
                ("page_street_key", address_key(page_address,
                                                identity["postal_code"])
                 if page_address else ""),
                ("street_key_agrees",
                 bool(page_address) and address_key(page_address, identity["postal_code"])
                 == address_key(identity["address"], identity["postal_code"])),
                ("census_phone_digits", re.sub(r"\D", "", identity["phone"] or "")),
                ("page_phone_digits", re.sub(r"\D", "", row["phone"] or "")),
                ("phone_agrees", bool(identity["phone"]) and bool(row["phone"])
                 and re.sub(r"\D", "", identity["phone"])[-10:]
                 == re.sub(r"\D", "", row["phone"])[-10:]),
                ("property_code_from_page_only", bool(row["property_code"])),
            ])),
            ("published_before", identity["normalized_name"] in published_keys),
            ("published_after", identity["normalized_name"] in published_keys),
        ]))

    outcome_counts = {name: sum(1 for i in items if i["outcome"] == name)
                      for name in OUTCOMES}
    shape_counts: Dict[str, int] = {}
    for item in items:
        if item["partition"] == "visible_policy":
            shape_counts[item["policy_wording_shape"]] = (
                shape_counts.get(item["policy_wording_shape"], 0) + 1)

    routing = [OrderedDict([
        ("slug", slug),
        ("canonical_name", census_by_slug[slug]["canonical_name"]),
        ("decision", decision),
        ("reason", reason),
        ("next_action", action),
    ]) for slug, (decision, reason, action) in ROUTING_ADJUDICATION.items()]

    return OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("run_id", RUN_ID),
        ("as_of", AS_OF),
        ("reviewer_id", REVIEWER),
        ("market_id", MARKET),
        ("input_package", OrderedDict([
            ("path", "data/operator_evidence/cleveland-founder-review-001/"
                     "incoming/work-browser-pass-001"),
            ("tracked", False),
            ("file_count", len(EXPECTED_FILES)),
            ("sha256", dict(input_hashes(directory))),
        ])),
        ("evidence_determination", OrderedDict([
            ("artifact_class", ARTIFACT_CLASS),
            ("verdict", ARTIFACT_VERDICT),
            ("screenshots", screenshot_inventory()),
            ("accepted_for_publication", False),
            ("accepted_for_routing_proposals", True),
            ("accepted_for_evidence_completion_queue", True),
        ])),
        ("reconciliation", reconciliation),
        ("outcome_counts", outcome_counts),
        ("visible_policy_wording_shapes", shape_counts),
        ("market_totals", OrderedDict([
            ("confirmed_identities", census["count"]),
            ("published_pet_friendly_before", len(published_keys)),
            ("published_pet_friendly_after", len(published_keys)),
            ("verified_no_pets_before", len(cleveland_exclusions)),
            ("verified_no_pets_after", len(cleveland_exclusions)),
            ("resolved_before", len(published_keys) + len(cleveland_exclusions)),
            ("resolved_after", len(published_keys) + len(cleveland_exclusions)),
            ("unresolved_before",
             census["count"] - len(published_keys) - len(cleveland_exclusions)),
            ("unresolved_after",
             census["count"] - len(published_keys) - len(cleveland_exclusions)),
        ])),
        ("routing_adjudication", routing),
        ("routing_accepted", sum(1 for r in routing if r["decision"] == ACCEPTED)),
        ("routing_rejected", sum(1 for r in routing if r["decision"] == REJECTED)),
        ("items", items),
    ])


def serialize(document: Mapping) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


def _write_lf(path: Path, text: str) -> None:
    """Write with LF endings on every platform.

    ``.gitattributes`` already normalises ``launch_packages/**/*.json`` to LF in
    the object store, so the committed blob would be right either way. Writing
    LF here keeps the WORKING TREE equal to the blob as well, which is what
    makes a byte comparison of two builds mean something on Windows.
    """
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write(document: Mapping = None, *, directory: Path = None) -> Dict:
    """Write the ledger and apply the one accepted routing correction."""
    doc = document if document is not None else build(directory)
    _write_lf(LEDGER_PATH, serialize(doc))

    routing_doc = _json(ROUTING_PATH)
    before_count = len(routing_doc["routes"])
    routing_doc, summary = apply_routing_correction(routing_doc)
    if len(routing_doc["routes"]) != before_count:
        raise WorkBrowserInputError("routing record count changed; refusing to write")
    _write_lf(ROUTING_PATH,
              json.dumps(routing_doc, indent=1, ensure_ascii=False) + "\n")
    return {"ledger": str(LEDGER_PATH), "routing": summary,
            "routes_before": before_count, "routes_after": len(routing_doc["routes"])}


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
        "  screenshots on disk ... %d file(s) in %d directories"
        % (document["evidence_determination"]["screenshots"]["files"],
           document["evidence_determination"]["screenshots"]["directories"]),
        "  routing accepted ...... %d   rejected %d"
        % (document["routing_accepted"], document["routing_rejected"]),
        "  published before/after  %d / %d"
        % (document["market_totals"]["published_pet_friendly_before"],
           document["market_totals"]["published_pet_friendly_after"]),
    ]
    for name in OUTCOMES:
        lines.append("  %-46s %d" % (name, document["outcome_counts"][name]))
    sys.stdout.write("\n".join(lines) + "\n")

    if "--apply" in argv:
        result = write(document)
        sys.stdout.write("wrote %s; routing %s -> %s\n"
                         % (result["ledger"], result["routing"]["before_url"],
                            result["routing"]["after_url"]))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
