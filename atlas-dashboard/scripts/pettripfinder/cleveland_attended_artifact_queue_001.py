"""PTF-CLEVELAND-ATTENDED-ARTIFACT-QUEUE-001 -- targeted evidence-artifact queue.

WHY THIS MODULE EXISTS
----------------------
``PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001`` reviewed 135 Cleveland
properties in an attended browser and wrote down what each page displayed.
``PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-002`` (commit ``be24c64``) joined that
review to committed authority and produced
``launch_packages/pettripfinder/cleveland_final_partition_002.json``: all 188
confirmed identities, each in exactly one final state, each with exactly one
next action.

That partition established the finding this module acts on. The browser package
is an ``OPERATOR_TRANSCRIBED_BROWSER_REVIEW`` -- the operator's typed record of
what a browser displayed -- and all 135 of its screenshot directories hold zero
image bytes. A transcription is research, not evidence: ``hotel_policy_facts``
requires a sha256 of a captured page or of an operator screenshot of that page,
``hotel_exclusions`` requires ``source_hash``, and policy membrane M9 can only be
enforced against a stored surface. So 70 Cleveland identities sit in
``AWAITING_POLICY_ARTIFACT`` with their policy WORDING known and no artifact of
the surface it was read from.

Not all 70 are worth the same trip. This module partitions the properties whose
blocker is specifically an image file into four non-overlapping queues, ordered
so the founder's first 32 captures are the ones that can actually change
Cleveland's published position:

  Queue A  AWAITING_POLICY_ARTIFACT + AFFIRMATIVE_STRUCTURED  -> publishable
  Queue B  AWAITING_POLICY_ARTIFACT + NEGATIVE                -> verified-no-pets
  Queue C  AWAITING_ATTENDED_CAPTURE                          -> surface is hidden
  Queue D  AWAITING_ROUTING_REVIEW                            -> identity only

WHAT IS DELIBERATELY NOT QUEUED
-------------------------------
The other 38 ``AWAITING_POLICY_ARTIFACT`` identities carry
``AFFIRMATIVE_MARKETING_ONLY`` wording -- "pet friendly guest rooms" with no fee,
weight, or count. A screenshot of marketing copy lands on ``POLICY_PARTIAL``
either way, so it does not clear this queue's bar of "an artifact here changes
the market's position". They keep their existing next action in the partition and
are named in the manifest's ``deliberately_not_queued`` block rather than
silently dropped.

``AWAITING_POLICY_OBSERVATION`` is likewise excluded: no policy has ever been
observed on those pages, so there is no wording for an artifact to bind. Sending
the founder to photograph a page that says nothing about pets would manufacture
work, not evidence.

WHAT THIS MODULE DOES NOT DO
----------------------------
It publishes nothing, excludes nothing, accepts no routing correction, and
modifies no authority file. It reads committed authority plus the untracked
operator package, and writes an untracked queue and an empty folder scaffold
under the gitignored ``data/`` tree. Queue D in particular carries a HELD routing
proposal and asks only for identity evidence -- never for pet-policy publication
evidence -- because combining a routing proposal with approved authority is
exactly the mistake the 002 work order was written to prevent.

``evidence_status`` is ``AWAITING_ARTIFACT`` for every row unless readable image
bytes are already on disk, which is checked by reading the PNG signature rather
than by trusting a filename.

Run:  python -m scripts.pettripfinder.cleveland_attended_artifact_queue_001 [--apply]
      python -m scripts.pettripfinder.cleveland_attended_artifact_queue_001 --validate
"""

from __future__ import annotations

import argparse
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

from scripts.pettripfinder import integrate_cleveland_work_browser_001 as WB   # noqa: E402
from scripts.pettripfinder.build_capture_queue import brand_for_url            # noqa: E402
from scripts.pettripfinder.identity_routing import registrable_domain          # noqa: E402

MARKET = "cleveland-akron-canton-oh"
RUN_ID = "cleveland-attended-artifact-001"
WORK_ORDER = "PTF-CLEVELAND-ATTENDED-ARTIFACT-QUEUE-001"
AS_OF = "2026-08-12"
REVIEWER = "jfields80"
SCHEMA = "ptf-attended-artifact-queue/1.0"

#: The authority this package was derived from. Recorded, not discovered, so the
#: manifest says the same thing in every clone.
SOURCE_COMMIT = "be24c6463ac652d17d0d291a3147ea8478f81d69"

# --------------------------------------------------------------------------- #
# Paths. Every default is repo-relative; every one is overridable, because the
# gitignored ``data/`` tree does not exist in a worktree and the evidence root
# is an absolute operator-facing location.
# --------------------------------------------------------------------------- #

PACKAGE_DIR = WB.INPUT_DIR
OUTPUT_ROOT = _REPO_ROOT / "data" / "operator_evidence"
OUTPUT_DIRNAME = RUN_ID

PARTITION_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                  / "cleveland_final_partition_002.json")
CENSUS_PATH = WB.CENSUS_PATH
FACTS_PATH = WB.FACTS_PATH
EXCLUSIONS_PATH = WB.EXCLUSIONS_PATH
SEED_PATH = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
DAYTON_CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                      / "identity_census" / "dayton-oh.json")

#: Tracked authority read by the generator, hashed into the manifest alongside
#: the 27 package files so a later pass can prove which inputs produced this.
AUTHORITY_INPUTS: Tuple[Tuple[str, Path], ...] = (
    ("launch_packages/pettripfinder/cleveland_final_partition_002.json", PARTITION_PATH),
    ("launch_packages/pettripfinder/identity_census/%s.json" % MARKET, CENSUS_PATH),
    ("launch_packages/pettripfinder/hotel_policy_facts_%s.json" % MARKET, FACTS_PATH),
    ("launch_packages/pettripfinder/hotel_exclusions.json", EXCLUSIONS_PATH),
    ("launch_packages/pettripfinder/seed_businesses.csv", SEED_PATH),
)

IDENTITY_FILENAME = "01-identity.png"
POLICY_FILENAME = "02-pet-policy.png"

QUEUE_A = "A"
QUEUE_B = "B"
QUEUE_C = "C"
QUEUE_D = "D"
QUEUE_ORDER = (QUEUE_A, QUEUE_B, QUEUE_C, QUEUE_D)

QUEUE_LABELS = {
    QUEUE_A: "HIGH_YIELD_AFFIRMATIVE_EVIDENCE",
    QUEUE_B: "HIGH_YIELD_NEGATIVE_EVIDENCE",
    QUEUE_C: "ATTENDED_INTERACTIVE_CAPTURE",
    QUEUE_D: "IDENTITY_ROUTING_EVIDENCE",
}

#: The rule that puts a property in a queue, stated once and reported in the
#: manifest verbatim. Membership is derived from committed authority only -- the
#: browser package supplies wording and provenance, never queue membership.
QUEUE_RULES = {
    QUEUE_A: ("final_state == AWAITING_POLICY_ARTIFACT and "
              "policy_wording_shape == AFFIRMATIVE_STRUCTURED"),
    QUEUE_B: ("final_state == AWAITING_POLICY_ARTIFACT and "
              "policy_wording_shape == NEGATIVE"),
    QUEUE_C: "final_state == AWAITING_ATTENDED_CAPTURE",
    QUEUE_D: "final_state == AWAITING_ROUTING_REVIEW",
}

QUEUE_PURPOSE = {
    QUEUE_A: ("Affirmative first-party pet-policy wording with an actionable term "
              "(fee, weight, or count) already preserved; an artifact of the page "
              "is the only thing between this property and publication."),
    QUEUE_B: ("Affirmative first-party wording that pets are NOT permitted; an "
              "artifact of the page is the only thing between this property and "
              "verified-no-pets authority. Silence, a missing policy block, or a "
              "failed page load is never in this queue."),
    QUEUE_C: ("The policy lives on the property's own surface but behind a click, "
              "an accordion, a modal, or client-side rendering. An attended "
              "browser is the lawful route; nothing here is a bypass."),
    QUEUE_D: ("A routing proposal is HELD because its destination cannot be "
              "confirmed first-party. This queue asks for IDENTITY evidence so "
              "the route can be adjudicated. It is not pet-policy publication "
              "evidence and must not be used as any."),
}

#: States excluded on purpose, each with the reason a screenshot would not help.
NOT_QUEUED_REASONS = {
    "AWAITING_POLICY_ARTIFACT_AFFIRMATIVE_MARKETING_ONLY": (
        "AWAITING_POLICY_ARTIFACT, but the preserved wording states no fee, weight "
        "or count. A capture of marketing copy lands on POLICY_PARTIAL either way, "
        "so an artifact does not change this property's position."),
    "AWAITING_POLICY_OBSERVATION": (
        "The route is sound and the page served its content, but no pet policy has "
        "ever been observed on it. There is no wording for an artifact to bind."),
    "AWAITING_ROUTING_REPLACEMENT": (
        "The URL on record is provably not this property's page. Photographing the "
        "wrong page is not evidence; routing must be repaired first."),
    "AWAITING_OFFICIAL_URL": (
        "No official URL has ever been found. There is nothing to open."),
    "AWAITING_PROPERTY_LEVEL_URL": (
        "Only a brand index or city-level URL is bound. Such a page is "
        "property-specific for nobody and cannot back a policy fact."),
    "AWAITING_CONTRADICTION_RESOLUTION": (
        "The evidence conflicts with itself. M8 forbids this layer from picking a "
        "winner; both surfaces must be captured together under approval_resolution, "
        "which is a different work order."),
    "AWAITING_CENSUS_REVIEW": (
        "The queued identity itself is in question. Census work, not evidence work."),
    "ACCESS_BLOCKED": (
        "An access-control wall stands between us and the property's own page and "
        "there is no lawful automated path."),
    "PUBLISHED_PET_FRIENDLY": "Already published; requeuing would duplicate authority.",
    "VERIFIED_NO_PETS": "Already excluded on a citable artifact.",
}

#: An eight-byte PNG signature. ``evidence_status`` flips only for a file that
#: actually starts with it -- a zero-byte or renamed placeholder stays
#: AWAITING_ARTIFACT.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: Columns of the machine-facing queue, in contract order. The founder-facing
#: CSV is a projection of these, never a separate derivation.
QUEUE_COLUMNS: Tuple[str, ...] = (
    "queue_id", "queue_class", "queue_label",
    "priority", "market_id", "hotel_id", "hotel_slug",
    "exact_hotel_name", "brand", "official_url", "browser_final_url",
    "property_code", "address", "city", "state", "zip", "phone",
    "browser_batch", "browser_row_id", "source_status",
    "exact_visible_policy_quote", "supported_candidate_facts", "withheld_facts",
    "routing_correction_status", "required_identity_screenshot",
    "required_policy_screenshot", "expected_identity_filename",
    "expected_policy_filename", "destination_folder", "one_next_action",
    "evidence_status",
    # Beyond the contract minimum, and each one earns its place: the founder has
    # to know which URL to open when it is not the one on record, and the next
    # integrator has to know why this row was classified as it was.
    "capture_url", "proposed_replacement_url", "property_code_status",
    "brand_source", "policy_wording_shape", "final_state",
    "work_browser_outcome", "work_browser_reason_code",
    "browser_contradictions_or_warnings", "browser_capture_warning",
)

FOUNDER_COLUMNS: Tuple[str, ...] = (
    "priority", "queue_id", "queue_class", "queue_label",
    "exact_hotel_name", "city", "state",
    "brand", "capture_url", "required_identity_screenshot",
    "required_policy_screenshot", "expected_identity_filename",
    "expected_policy_filename", "destination_folder", "one_next_action",
    "evidence_status",
)


class AttendedQueueError(RuntimeError):
    """The inputs do not support the queue this module claims to build."""


# --------------------------------------------------------------------------- #
# Inputs.
# --------------------------------------------------------------------------- #

def input_present(package_dir: Optional[Path] = None) -> bool:
    """True when the untracked operator package is on this machine.

    Callers declare the package as a precondition and skip with the path named,
    the ``ed53d5b``/``441498d`` pattern established after a worktree with no
    ``data/`` reported nine phantom failures.
    """
    base = Path(package_dir) if package_dir else PACKAGE_DIR
    return base.is_dir() and (base / WB.EXPECTED_FILES[0]).exists()


def _json(path: Path) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture_warnings(package_dir: Optional[Path] = None) -> Dict[str, str]:
    """slug -> the warning the browser pass recorded while it was on that page.

    The outgoing screenshot queue covers 129 of the 135 reviewed properties; a
    slug it never listed simply has no warning, which is not the same as a clean
    capture and is reported as an empty string either way.
    """
    base = Path(package_dir) if package_dir else PACKAGE_DIR
    path = base / "work-browser-screenshot-queue.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {str(row.get("slug", "")).strip():
                str(row.get("any capture warning", "") or "").strip()
                for row in csv.DictReader(handle)}


def browser_rows_by_slug(package_dir: Optional[Path] = None) -> Dict[str, Dict]:
    """The 135 reviewed rows keyed by slug, with a stable per-row citation.

    ``WB.load_rows`` already normalises batch 2's separate 24-column schema onto
    the same field names, which is the whole reason this module reuses it rather
    than re-parsing the CSVs: the row that the 002 work order found had been
    skipped is a batch-2 row, and it is Queue D here.
    """
    base = Path(package_dir) if package_dir else PACKAGE_DIR
    rows = WB.load_rows(base)
    indexed: Dict[str, Dict] = {}
    seen_per_batch: Dict[int, int] = {}
    for row in rows:
        batch = int(row["batch"])
        seen_per_batch[batch] = seen_per_batch.get(batch, 0) + 1
        row = dict(row)
        row["row_id"] = "batch-%03d-review.csv#row%d" % (batch, seen_per_batch[batch])
        slug = row["slug"]
        if slug in indexed:
            raise AttendedQueueError(
                "duplicate slug in the browser package: %s" % slug)
        indexed[slug] = row
    return indexed


# --------------------------------------------------------------------------- #
# Queue membership. Derived from the committed partition, never from the CSVs.
# --------------------------------------------------------------------------- #

def queue_class_of(item: Mapping) -> str:
    """The queue this identity belongs to, or ``""`` for none.

    Exactly one branch can match: the four rules are keyed on ``final_state``,
    which the partition guarantees is single-valued, and the only state that
    splits (``AWAITING_POLICY_ARTIFACT``) splits on a shape vocabulary that is
    itself closed and single-valued.
    """
    state = item.get("final_state", "")
    shape = item.get("policy_wording_shape", "")
    if state == "AWAITING_POLICY_ARTIFACT":
        if shape == "AFFIRMATIVE_STRUCTURED":
            return QUEUE_A
        if shape == "NEGATIVE":
            return QUEUE_B
        return ""
    if state == "AWAITING_ATTENDED_CAPTURE":
        return QUEUE_C
    if state == "AWAITING_ROUTING_REVIEW":
        return QUEUE_D
    return ""


def market_key(name: str) -> str:
    """A cross-market comparison key: letters and digits only, lowercased.

    Used only to prove a queued property is not a Columbus or Dayton hotel under
    a differently punctuated spelling. It is never a join key for authority.
    """
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def _brand_of(capture_url: str, final_url: str) -> Tuple[str, str]:
    """The operator of the page the founder will actually be looking at.

    Tried in order: the URL to open, then the URL the browser pass observed it
    resolve to. The second step is what keeps IHG together -- six Queue C rows
    are bound to brand short domains (``holidayinn.com``, ``holiday-inn.com``,
    ``hiexpress.com``, ``crowneplaza.com``) that all redirect to ``ihg.com``, and
    grouping them as four different "brands" would send the founder through the
    same site four separate times. The redirect is observed, not assumed: it is
    in the browser pass's recorded final URL.
    """
    for url, source in ((capture_url, "BRAND_DOMAIN_MAP"),
                        (final_url, "BRAND_DOMAIN_MAP_VIA_OBSERVED_FINAL_URL")):
        slug = brand_for_url(url)
        if slug:
            return slug, source
    domain = registrable_domain(capture_url)
    return (domain, "REGISTRABLE_DOMAIN_FALLBACK") if domain else ("", "NONE")


def _readable_png(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(_PNG_SIGNATURE)) == _PNG_SIGNATURE
    except OSError:
        return False


def existing_artifacts(folder: Path) -> List[str]:
    """Filenames in ``folder`` that really are readable image bytes."""
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir()
                  if p.is_file() and _readable_png(p))


def _next_action(queue_class: str, capture_url: str, folder: str) -> str:
    if queue_class == QUEUE_A:
        return ("Screenshot the pet-policy block and the identity block shown on "
                "%s into %s." % (capture_url, folder))
    if queue_class == QUEUE_B:
        return ("Screenshot the refusal wording and the identity block shown on "
                "%s into %s." % (capture_url, folder))
    if queue_class == QUEUE_C:
        return ("Open %s, expand the pet-policy surface (accordion, modal, or "
                "'pet policy' link), and screenshot it together with the identity "
                "block into %s." % (capture_url, folder))
    return ("Screenshot ONLY the identity block (exact hotel name, street, city, "
            "state, ZIP, phone) shown on %s into %s; this is routing evidence and "
            "is not pet-policy publication evidence." % (capture_url, folder))


# --------------------------------------------------------------------------- #
# Build.
# --------------------------------------------------------------------------- #

def build_rows(*, package_dir: Optional[Path] = None,
               output_dir: Optional[Path] = None,
               partition: Optional[Mapping] = None,
               census: Optional[Mapping] = None) -> List["OrderedDict[str, str]"]:
    """One row per queued property, ordered exactly as the founder works them.

    Ordering is (queue class, brand, city, hotel name). Grouping by brand inside
    a class is not cosmetic: consecutive rows land on the same site with the same
    cookie banner and the same page furniture, which is what makes 32 captures a
    single sitting instead of 32 separate ones.
    """
    partition = partition if partition is not None else _json(PARTITION_PATH)
    census = census if census is not None else _json(CENSUS_PATH)
    out_dir = Path(output_dir) if output_dir else (OUTPUT_ROOT / OUTPUT_DIRNAME)
    shots_root = out_dir / "screenshots"

    browser = browser_rows_by_slug(package_dir)
    warnings = capture_warnings(package_dir)
    census_by_name = {h["normalized_name"]: h for h in census["hotels"]}

    staged: List[Tuple[Tuple, Mapping, Mapping]] = []
    for item in partition["items"]:
        klass = queue_class_of(item)
        if not klass:
            continue
        slug = item["slug"]
        row = browser.get(slug)
        if row is None:
            raise AttendedQueueError(
                "%s is queued but has no row in the browser package; every queue "
                "class in this package is defined by a state only a reviewed "
                "property can hold" % slug)
        identity = census_by_name.get(item["normalized_name"])
        if identity is None:
            raise AttendedQueueError(
                "%s is queued but is not in the %s census" % (slug, MARKET))
        replacement = row.get("replacement_url", "") or ""
        # Queue D's recorded vanity domain returns 502, so the URL to OPEN is the
        # proposal under review. Every other class opens the URL on record; a
        # proposal that pass 001 rejected does not become the capture target
        # because the founder happens to be looking at the property.
        capture_url = (replacement if klass == QUEUE_D and replacement
                       else item["official_url"])
        brand, brand_source = _brand_of(capture_url, row.get("final_url", ""))
        sort_key = (QUEUE_ORDER.index(klass), brand, identity.get("city", ""),
                    item["canonical_name"].casefold(), slug)
        staged.append((sort_key, item, {"row": row, "identity": identity,
                                        "brand": brand, "capture_url": capture_url,
                                        "replacement_url": replacement,
                                        "brand_source": brand_source}))
    staged.sort(key=lambda entry: entry[0])

    per_class: Dict[str, int] = {}
    rows: List["OrderedDict[str, str]"] = []
    for priority, (_, item, extra) in enumerate(staged, start=1):
        klass = queue_class_of(item)
        per_class[klass] = per_class.get(klass, 0) + 1
        row, identity = extra["row"], extra["identity"]
        slug = item["slug"]

        replacement = extra["replacement_url"]
        capture_url = extra["capture_url"]
        folder = shots_root / slug
        folder_text = str(folder)
        needs_policy = klass != QUEUE_D
        present = existing_artifacts(folder)

        rows.append(OrderedDict((
            ("queue_id", "CLE-AAQ-001-%s%02d" % (klass, per_class[klass])),
            ("queue_class", klass),
            ("queue_label", QUEUE_LABELS[klass]),
            ("priority", str(priority)),
            ("market_id", MARKET),
            ("hotel_id", item["normalized_name"]),
            ("hotel_slug", slug),
            ("exact_hotel_name", item["canonical_name"]),
            ("brand", extra["brand"]),
            ("official_url", item["official_url"]),
            ("browser_final_url", row.get("final_url", "")),
            ("property_code", row.get("property_code", "")),
            ("address", identity.get("address", "")),
            ("city", identity.get("city", "")),
            ("state", identity.get("state", "")),
            ("zip", identity.get("postal_code", "")),
            ("phone", identity.get("phone", "")),
            ("browser_batch", str(row["batch"])),
            ("browser_row_id", row["row_id"]),
            ("source_status", row.get("classification", "")),
            ("exact_visible_policy_quote", row.get("policy_text", "")),
            ("supported_candidate_facts", row.get("supported", "")),
            ("withheld_facts", row.get("withheld", "")),
            ("routing_correction_status", row.get("routing_status", "") or "NONE"),
            ("required_identity_screenshot", "YES"),
            ("required_policy_screenshot", "YES" if needs_policy else "NO"),
            ("expected_identity_filename", IDENTITY_FILENAME),
            ("expected_policy_filename", POLICY_FILENAME if needs_policy else ""),
            ("destination_folder", folder_text),
            ("one_next_action", _next_action(klass, capture_url, folder_text)),
            ("evidence_status",
             "ARTIFACT_PRESENT" if present else "AWAITING_ARTIFACT"),
            ("capture_url", capture_url),
            ("proposed_replacement_url", replacement),
            ("property_code_status",
             "DISPLAYED" if row.get("property_code") else "NOT_DISPLAYED"),
            ("brand_source", extra["brand_source"]),
            ("policy_wording_shape", item["policy_wording_shape"]),
            ("final_state", item["final_state"]),
            ("work_browser_outcome", item["work_browser_outcome"]),
            ("work_browser_reason_code", item["work_browser_reason_code"]),
            ("browser_contradictions_or_warnings", row.get("contradictions", "")),
            ("browser_capture_warning", warnings.get(slug, "")),
        )))
    return rows


def not_queued(partition: Mapping) -> "OrderedDict[str, List[Dict[str, str]]]":
    """Every unqueued identity, grouped by the reason a screenshot would not help.

    Reported so the manifest accounts for all 188 identities, not just the 47
    this package acts on. An omission that is never named is indistinguishable
    from an omission that was never noticed.
    """
    grouped: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict()
    for item in partition["items"]:
        if queue_class_of(item):
            continue
        state = item["final_state"]
        # AWAITING_POLICY_ARTIFACT is the only unqueued state whose members
        # differ in kind, so it is grouped by wording shape and everything else
        # by its state.
        key = ("%s_%s" % (state, item["policy_wording_shape"])
               if state == "AWAITING_POLICY_ARTIFACT" else state)
        grouped.setdefault(key, []).append(
            {"slug": item["slug"], "canonical_name": item["canonical_name"],
             "final_state": state,
             "policy_wording_shape": item["policy_wording_shape"]})
    for entries in grouped.values():
        entries.sort(key=lambda e: e["slug"])
    return OrderedDict(sorted(grouped.items()))


# --------------------------------------------------------------------------- #
# Validation. Each check is a named assertion with its own evidence, so a
# failure says which rule broke rather than that "validation failed".
# --------------------------------------------------------------------------- #

def _check(name: str, passed: bool, detail: str) -> Dict[str, object]:
    return {"check": name, "passed": bool(passed), "detail": detail}


def validate(rows: Sequence[Mapping], *, partition: Mapping,
             census: Mapping, facts: Mapping, exclusions: Mapping,
             seed_rows: Sequence[Mapping], dayton_census: Optional[Mapping],
             output_dir: Path,
             input_hashes: Mapping[str, str]) -> List[Dict[str, object]]:
    checks: List[Dict[str, object]] = []
    slugs = [r["hotel_slug"] for r in rows]
    members = {k: [r["hotel_slug"] for r in rows if r["queue_class"] == k]
               for k in QUEUE_ORDER}
    counts = {k: len(v) for k, v in members.items()}

    checks.append(_check(
        "every_queued_hotel_appears_exactly_once",
        len(slugs) == len(set(slugs)),
        "%d rows, %d distinct slugs" % (len(slugs), len(set(slugs)))))

    overlaps = sorted(
        set(members[a]) & set(members[b])
        for i, a in enumerate(QUEUE_ORDER) for b in QUEUE_ORDER[i + 1:])
    shared = sorted({s for group in overlaps for s in group})
    checks.append(_check(
        "no_hotel_in_two_queue_classes",
        not shared and sum(counts.values()) == len(slugs),
        "queue classes are pairwise disjoint and cover every row; shared=%s"
        % shared))

    published = {h["name"].strip().lower() for h in facts["hotels"]}
    queued_names = {r["exact_hotel_name"].strip().lower() for r in rows}
    checks.append(_check(
        "no_published_hotel_requeued",
        published.isdisjoint(queued_names),
        "%d published Cleveland hotels; overlap=%s"
        % (len(published), sorted(published & queued_names))))

    excluded = {e["canonical_name"].strip().lower()
                for e in exclusions["exclusions"] if e["market_id"] == MARKET}
    checks.append(_check(
        "no_verified_no_pets_hotel_requeued",
        excluded.isdisjoint(queued_names),
        "%d Cleveland exclusions; overlap=%s"
        % (len(excluded), sorted(excluded & queued_names))))

    checks.append(_check(
        "no_published_or_excluded_final_state_queued",
        all(r["final_state"] not in ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS")
            for r in rows),
        "queued final states: %s"
        % ",".join(sorted({r["final_state"] for r in rows}))))

    foreign = {market_key(r["name"]) for r in seed_rows
               if r.get("market_id") in ("columbus-oh", "dayton-oh")}
    if dayton_census:
        foreign |= {market_key(h["canonical_name"])
                    for h in dayton_census["hotels"]}
    hit = sorted(r["hotel_slug"] for r in rows
                 if market_key(r["exact_hotel_name"]) in foreign)
    checks.append(_check(
        "no_columbus_or_dayton_property_queued",
        not hit,
        "compared against %d Columbus/Dayton names; hits=%s" % (len(foreign), hit)))

    census_names = {h["normalized_name"] for h in census["hotels"]}
    missing = sorted(r["hotel_slug"] for r in rows
                     if r["hotel_id"] not in census_names)
    checks.append(_check(
        "every_queued_hotel_is_in_the_cleveland_census",
        not missing,
        "census holds %d identities; not found=%s" % (len(census_names), missing)))

    confirmed = {h["normalized_name"] for h in census["hotels"]
                 if h.get("identity_state") == "IDENTITY_CONFIRMED"}
    unconfirmed = sorted(r["hotel_slug"] for r in rows
                         if r["hotel_id"] not in confirmed)
    checks.append(_check(
        "every_queued_hotel_is_identity_confirmed",
        not unconfirmed,
        "unconfirmed=%s" % unconfirmed))

    checks.append(_check(
        "every_row_has_exactly_one_next_action",
        all(r["one_next_action"].strip() and "\n" not in r["one_next_action"]
            for r in rows),
        "%d single-statement actions" % len(rows)))

    checks.append(_check(
        "every_row_has_a_capture_url",
        all(r["capture_url"].strip().startswith("http") for r in rows),
        "%d rows carry an absolute URL to open" % len(rows)))

    folders = [Path(r["destination_folder"]) for r in rows]
    absent = sorted(str(f) for f in folders if not f.is_dir())
    checks.append(_check(
        "every_destination_folder_exists",
        not absent,
        "%d folders; absent=%s" % (len(folders), absent[:5])))

    checks.append(_check(
        "every_destination_folder_is_inside_the_evidence_root",
        all(str(f).startswith(str(Path(output_dir) / "screenshots")) for f in folders),
        "root=%s" % (Path(output_dir) / "screenshots")))

    deterministic = all(
        r["expected_identity_filename"] == IDENTITY_FILENAME
        and (r["expected_policy_filename"] == POLICY_FILENAME
             if r["required_policy_screenshot"] == "YES"
             else r["expected_policy_filename"] == "")
        for r in rows)
    checks.append(_check(
        "expected_filenames_are_deterministic",
        deterministic,
        "identity=%s policy=%s, policy filename present iff required"
        % (IDENTITY_FILENAME, POLICY_FILENAME)))

    a_bad = sorted(r["hotel_slug"] for r in rows
                   if r["queue_class"] == QUEUE_A
                   and WB.policy_shape(r["exact_visible_policy_quote"])
                   != "AFFIRMATIVE_STRUCTURED")
    checks.append(_check(
        "queue_a_quotes_re_derive_as_affirmative_structured",
        not a_bad,
        "re-derived with the pass-001 classifier; mismatches=%s" % a_bad))

    b_bad = sorted(r["hotel_slug"] for r in rows
                   if r["queue_class"] == QUEUE_B
                   and WB.policy_shape(r["exact_visible_policy_quote"]) != "NEGATIVE")
    checks.append(_check(
        "queue_b_quotes_re_derive_as_negative",
        not b_bad,
        "silence and page failures cannot enter Queue B; mismatches=%s" % b_bad))

    checks.append(_check(
        "queue_b_carries_no_empty_quote",
        all(r["exact_visible_policy_quote"].strip() for r in rows
            if r["queue_class"] == QUEUE_B),
        "%d negative-evidence rows, each with preserved wording" % counts[QUEUE_B]))

    checks.append(_check(
        "queue_d_requests_identity_evidence_only",
        all(r["required_policy_screenshot"] == "NO"
            and r["expected_policy_filename"] == ""
            for r in rows if r["queue_class"] == QUEUE_D),
        "%d routing-review rows, none asking for policy evidence" % counts[QUEUE_D]))

    checks.append(_check(
        "no_property_code_inferred",
        all(r["property_code"] == "" or r["property_code_status"] == "DISPLAYED"
            for r in rows),
        "a code is carried only where the page displayed one"))

    derived = {"A": sum(1 for i in partition["items"]
                        if queue_class_of(i) == QUEUE_A),
               "B": sum(1 for i in partition["items"]
                        if queue_class_of(i) == QUEUE_B),
               "C": sum(1 for i in partition["items"]
                        if queue_class_of(i) == QUEUE_C),
               "D": sum(1 for i in partition["items"]
                        if queue_class_of(i) == QUEUE_D)}
    checks.append(_check(
        "queue_totals_equal_the_partition_they_were_derived_from",
        derived == counts,
        "partition=%s rows=%s" % (derived, counts)))

    state_counts = partition["final_state_counts"]
    checks.append(_check(
        "queue_c_equals_awaiting_attended_capture",
        counts[QUEUE_C] == state_counts["AWAITING_ATTENDED_CAPTURE"],
        "%d == %d" % (counts[QUEUE_C], state_counts["AWAITING_ATTENDED_CAPTURE"])))
    checks.append(_check(
        "queue_d_equals_awaiting_routing_review",
        counts[QUEUE_D] == state_counts["AWAITING_ROUTING_REVIEW"],
        "%d == %d" % (counts[QUEUE_D], state_counts["AWAITING_ROUTING_REVIEW"])))
    checks.append(_check(
        "queue_a_plus_b_are_a_subset_of_awaiting_policy_artifact",
        counts[QUEUE_A] + counts[QUEUE_B]
        <= state_counts["AWAITING_POLICY_ARTIFACT"],
        "%d + %d <= %d" % (counts[QUEUE_A], counts[QUEUE_B],
                           state_counts["AWAITING_POLICY_ARTIFACT"])))

    accounted = len(rows) + sum(len(v) for v in not_queued(partition).values())
    checks.append(_check(
        "every_census_identity_is_queued_or_explained",
        accounted == len(partition["items"]) == census["count"],
        "%d queued + explained == %d partition items == %d census"
        % (accounted, len(partition["items"]), census["count"])))

    expected_inputs = len(WB.EXPECTED_FILES) + len(AUTHORITY_INPUTS)
    checks.append(_check(
        "sha256_recorded_for_every_input",
        len(input_hashes) == expected_inputs
        and all(v.startswith("sha256:") for v in input_hashes.values()),
        "%d of %d inputs hashed" % (len(input_hashes), expected_inputs)))

    claimed = [r["hotel_slug"] for r in rows
               if r["evidence_status"] != "AWAITING_ARTIFACT"]
    on_disk = {r["hotel_slug"]: existing_artifacts(Path(r["destination_folder"]))
               for r in rows}
    checks.append(_check(
        "no_screenshot_claimed_without_readable_image_bytes",
        all(on_disk[s] for s in claimed),
        "%d rows claim an artifact; %d readable image files on disk"
        % (len(claimed), sum(len(v) for v in on_disk.values()))))

    return checks


# --------------------------------------------------------------------------- #
# Serialisation.
# --------------------------------------------------------------------------- #

def _csv_text(rows: Sequence[Mapping], columns: Sequence[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns),
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return buffer.getvalue()


def _write_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def build_manifest(rows: Sequence[Mapping], *, partition: Mapping,
                   census: Mapping, facts: Mapping, exclusions: Mapping,
                   output_dir: Path, input_hashes: Mapping[str, str],
                   checks: Sequence[Mapping],
                   package_dir: Path) -> "OrderedDict[str, object]":
    counts = {k: sum(1 for r in rows if r["queue_class"] == k)
              for k in QUEUE_ORDER}
    by_slug = {i["slug"]: i for i in partition["items"]}
    # The prior pass's screenshot tree is a sibling of its ``incoming/`` folder,
    # so it is located from the package that was actually read rather than from
    # a repo-relative default that resolves to nothing in a worktree.
    shots = WB.screenshot_inventory(
        Path(package_dir).parent.parent / "screenshots")

    queues = OrderedDict()
    for klass in QUEUE_ORDER:
        members = [r for r in rows if r["queue_class"] == klass]
        queues[klass] = OrderedDict((
            ("label", QUEUE_LABELS[klass]),
            ("membership_rule", QUEUE_RULES[klass]),
            ("purpose", QUEUE_PURPOSE[klass]),
            ("count", len(members)),
            ("items", [OrderedDict((
                ("queue_id", r["queue_id"]),
                ("priority", int(r["priority"])),
                ("hotel_slug", r["hotel_slug"]),
                ("hotel_id", r["hotel_id"]),
                ("exact_hotel_name", r["exact_hotel_name"]),
                ("brand", r["brand"]),
                ("city", r["city"]),
                ("capture_url", r["capture_url"]),
                ("required_screenshots",
                 [IDENTITY_FILENAME] + ([POLICY_FILENAME]
                                        if r["required_policy_screenshot"] == "YES"
                                        else [])),
                ("destination_folder", r["destination_folder"]),
                ("evidence_status", r["evidence_status"]),
                ("browser_row_id", r["browser_row_id"]),
                # The action this package hands the founder is an operator
                # instruction. The blocker action recorded by the authority that
                # last examined the property is carried here as provenance, so
                # the CSV keeps exactly one action per row.
                ("carried_blocker_action",
                 by_slug[r["hotel_slug"]]["next_action"]),
                ("carried_blocker_action_source",
                 by_slug[r["hotel_slug"]]["next_action_source"]),
            )) for r in members]),
        ))

    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("run_id", RUN_ID),
        ("as_of", AS_OF),
        ("reviewer_id", REVIEWER),
        ("market_id", MARKET),
        ("source_commit", SOURCE_COMMIT),
        ("evidence_root", str(output_dir)),
        ("note",
         "A packaging and evidence-collection preparation artifact. It publishes "
         "nothing, excludes nothing, accepts no routing correction, and modifies "
         "no authority file. Queue membership is derived from "
         "cleveland_final_partition_002.json; the operator browser package "
         "supplies wording, provenance and warnings only."),
        ("evidence_determination", OrderedDict((
            ("browser_package_artifact_class", WB.ARTIFACT_CLASS),
            ("publishable_without_a_page_artifact", False),
            ("screenshot_census_of_the_prior_pass", shots),
            ("screenshots_claimed_by_this_package", 0),
            ("why", WB.ARTIFACT_VERDICT),
        ))),
        ("reconciliation", OrderedDict((
            ("confirmed_identities", census["count"]),
            ("published_pet_friendly", len(facts["hotels"])),
            ("verified_no_pets", sum(1 for e in exclusions["exclusions"]
                                     if e["market_id"] == MARKET)),
            ("resolved", partition["reconciliation"]["resolved"]),
            ("unresolved", partition["reconciliation"]["unresolved"]),
            ("reviewed_in_work_browser_pass_001",
             partition["reconciliation"]["reviewed_in_work_browser_pass_001"]),
            ("derived_from",
             "counted from the census, the Cleveland policy-facts package and the "
             "Cleveland rows of hotel_exclusions.json at this run, not copied "
             "from the work order"),
        ))),
        ("partition_final_state_counts", partition["final_state_counts"]),
        ("queue_totals", OrderedDict((
            ("A", counts[QUEUE_A]), ("B", counts[QUEUE_B]),
            ("C", counts[QUEUE_C]), ("D", counts[QUEUE_D]),
            ("total", len(rows)),
        ))),
        ("expected_vs_derived", OrderedDict((
            ("stated_in_work_order",
             {"A": 17, "B": 15, "C": 14, "D": 1, "awaiting_policy_artifact": 70}),
            ("mechanically_derived",
             {"A": counts[QUEUE_A], "B": counts[QUEUE_B], "C": counts[QUEUE_C],
              "D": counts[QUEUE_D],
              "awaiting_policy_artifact":
                  partition["final_state_counts"]["AWAITING_POLICY_ARTIFACT"]}),
            ("agree",
             counts[QUEUE_A] == 17 and counts[QUEUE_B] == 15
             and counts[QUEUE_C] == 14 and counts[QUEUE_D] == 1
             and partition["final_state_counts"]["AWAITING_POLICY_ARTIFACT"] == 70),
        ))),
        ("queues", queues),
        ("deliberately_not_queued", OrderedDict(
            (key, OrderedDict((("reason", NOT_QUEUED_REASONS.get(key, "")),
                               ("count", len(entries)),
                               ("items", entries))))
            for key, entries in not_queued(partition).items())),
        ("files_written", [
            "cleveland-attended-artifact-queue.csv",
            "work-browser-targeted-queue.csv",
            "manifest.json",
            "README.txt",
            "screenshots/<hotel-slug>/ (%d directories, all empty)" % len(rows),
        ]),
        ("input_files_sha256", OrderedDict(input_hashes)),
        ("input_package_dir", str(package_dir)),
        ("validation", list(checks)),
        ("validation_passed", all(c["passed"] for c in checks)),
        ("not_done", [
            "no browser research was rerun",
            "no page was fetched, probed or automated",
            "no hotel was published",
            "no exclusion was written",
            "no routing correction was accepted",
            "no authority file was modified",
            "no build, deploy, Netlify or DNS action occurred",
        ]),
    ))


README_TEMPLATE = """\
{work_order}
Cleveland-Akron-Canton, OH -- targeted screenshot evidence queue
==========================================================================

EVIDENCE ROOT (this exact path)

    {root}\\

WHAT THIS IS
------------
{total} properties that are waiting on one thing: a picture of the page.

The earlier browser pass typed out what {reviewed} Cleveland hotel pages
displayed. That is research, not evidence -- Atlas cannot publish a pet policy
or record a no-pets exclusion without a stored artifact of the surface the
wording was read from. These {total} properties already have the wording. They
need the screenshot.

Nothing in this folder changes Atlas. Nothing is published until the images
exist and a later work order ingests them.

HOW TO WORK IT
--------------
 1. Open work-browser-targeted-queue.csv. It is sorted in the order to work.
 2. Do Queue A and Queue B first -- rows 1 to {high_yield}. Those are the ones
    that can change Cleveland's published position today.
 3. For each row, open the URL in the capture_url column.
 4. Save the requested screenshot into the hotel folder named in the
    destination_folder column. The folder already exists; do not create,
    rename, or move folders.
 5. Use the exact filename the row asks for:
        {identity_filename}   the hotel's name, street address, city, state, ZIP, and
                         phone if the page shows one
        {policy_filename}  the complete pet-policy wording, with every fee, stay
                         band, weight limit, pet count and restriction visible,
                         and enough of the page around it to show it is not
                         detached text
 6. Do not edit any wording in the CSV. If something is wrong, leave it and say
    so in your handback note.
 7. Do not create evidence for a page that is blocked, or for a page whose hotel
    name and address do not match the row. A screenshot of the wrong hotel is
    worse than no screenshot.
 8. If a page is blocked, times out, or shows a bot check, record that honestly
    and move to the next row. A blocked page is a normal outcome and is never a
    reason to keep clicking.
 9. Queue C comes after the {high_yield} high-yield properties. Those pages hide
    the pet policy behind a click, an accordion, or a modal -- open it first,
    then capture it together with the identity block.
10. Queue D is identity evidence, not pet-policy publication evidence. It asks
    only for {identity_filename}, to settle which hotel a proposed URL actually points
    at. Do not capture or submit a pet policy for it.

QUEUE SIZES (derived from committed authority, not copied from a plan)
----------------------------------------------------------------------
    Queue A  high-yield affirmative evidence ..... {a}
    Queue B  high-yield negative evidence ........ {b}
    Queue C  attended interactive capture ........ {c}
    Queue D  identity / routing evidence ......... {d}
                                                  ----
    Total .......................................  {total}

ONE PROPERTY NEEDS EXTRA CARE
-----------------------------
{queue_d_note}

WHAT IS IN THIS FOLDER
----------------------
    work-browser-targeted-queue.csv     the founder worksheet -- start here
    cleveland-attended-artifact-queue.csv   the full record, one row per
                                        property, every field the next
                                        integrator needs
    manifest.json                       counts, membership rules, input hashes,
                                        and the validation results
    README.txt                          this file
    screenshots\\<hotel-slug>\\           one empty folder per queued property

Every folder is empty right now, and manifest.json says so. That is correct:
this package claims zero screenshots because zero image bytes exist.
"""


def render_readme(rows: Sequence[Mapping], output_dir: Path,
                  reviewed: int) -> str:
    counts = {k: sum(1 for r in rows if r["queue_class"] == k)
              for k in QUEUE_ORDER}
    d_rows = [r for r in rows if r["queue_class"] == QUEUE_D]
    if d_rows:
        d = d_rows[0]
        note = (
            "%s (row %s).\n"
            "The URL Atlas has on record for it is dead, and the URL in this\n"
            "row is a PROPOSED replacement that has not been accepted. Capture\n"
            "%s only, and check before you do that the page you are\n"
            "looking at shows that exact hotel name and street address. Several\n"
            "Hyatt Place properties in this market share a brand and a city\n"
            "name; the Westlake / Crocker Park property must not be confused\n"
            "with any other Hyatt. If the page shows a different hotel, capture\n"
            "nothing and say so."
            % (d["exact_hotel_name"], d["priority"], IDENTITY_FILENAME))
    else:
        note = "None in this package."
    return README_TEMPLATE.format(
        work_order=WORK_ORDER, root=str(output_dir), total=len(rows),
        reviewed=reviewed, high_yield=counts[QUEUE_A] + counts[QUEUE_B],
        a=counts[QUEUE_A], b=counts[QUEUE_B], c=counts[QUEUE_C],
        d=counts[QUEUE_D], identity_filename=IDENTITY_FILENAME,
        policy_filename=POLICY_FILENAME, queue_d_note=note)


def collect_input_hashes(package_dir: Path) -> "OrderedDict[str, str]":
    hashes: "OrderedDict[str, str]" = OrderedDict()
    for name, value in WB.input_hashes(package_dir).items():
        hashes["data/operator_evidence/cleveland-founder-review-001/incoming/"
               "work-browser-pass-001/" + name] = value
    for label, path in AUTHORITY_INPUTS:
        hashes[label] = sha256_file(path)
    return hashes


def build(*, package_dir: Optional[Path] = None,
          output_dir: Optional[Path] = None) -> Dict[str, object]:
    """Everything this package consists of, computed but not yet written."""
    pkg = Path(package_dir) if package_dir else PACKAGE_DIR
    out = Path(output_dir) if output_dir else (OUTPUT_ROOT / OUTPUT_DIRNAME)

    partition = _json(PARTITION_PATH)
    census = _json(CENSUS_PATH)
    facts = _json(FACTS_PATH)
    exclusions = _json(EXCLUSIONS_PATH)
    dayton = _json(DAYTON_CENSUS_PATH) if DAYTON_CENSUS_PATH.exists() else None
    with SEED_PATH.open(encoding="utf-8-sig", newline="") as handle:
        seed_rows = list(csv.DictReader(handle))

    rows = build_rows(package_dir=pkg, output_dir=out,
                      partition=partition, census=census)
    return {"rows": rows, "partition": partition, "census": census,
            "facts": facts, "exclusions": exclusions, "dayton": dayton,
            "seed_rows": seed_rows, "output_dir": out, "package_dir": pkg}


def write(*, package_dir: Optional[Path] = None,
          output_dir: Optional[Path] = None) -> Dict[str, object]:
    """Create the folder scaffold, then the queue files, then validate on disk.

    The order matters: ``every_destination_folder_exists`` is only a real check
    if the folders were made before it ran.
    """
    state = build(package_dir=package_dir, output_dir=output_dir)
    rows, out = state["rows"], state["output_dir"]

    out.mkdir(parents=True, exist_ok=True)
    (out / "screenshots").mkdir(exist_ok=True)
    for row in rows:
        Path(row["destination_folder"]).mkdir(parents=True, exist_ok=True)

    hashes = collect_input_hashes(state["package_dir"])
    checks = validate(rows, partition=state["partition"], census=state["census"],
                      facts=state["facts"], exclusions=state["exclusions"],
                      seed_rows=state["seed_rows"], dayton_census=state["dayton"],
                      output_dir=out, input_hashes=hashes)
    manifest = build_manifest(
        rows, partition=state["partition"], census=state["census"],
        facts=state["facts"], exclusions=state["exclusions"], output_dir=out,
        input_hashes=hashes, checks=checks, package_dir=state["package_dir"])

    _write_lf(out / "cleveland-attended-artifact-queue.csv",
              _csv_text(rows, QUEUE_COLUMNS))
    _write_lf(out / "work-browser-targeted-queue.csv",
              _csv_text(rows, FOUNDER_COLUMNS))
    _write_lf(out / "manifest.json",
              json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    _write_lf(out / "README.txt",
              render_readme(rows, out,
                            state["partition"]["reconciliation"]
                            ["reviewed_in_work_browser_pass_001"]))

    state["manifest"] = manifest
    state["checks"] = checks
    return state


def validate_on_disk(output_dir: Optional[Path] = None) -> Dict[str, object]:
    """Re-check a package that is already on disk, without rewriting it."""
    out = Path(output_dir) if output_dir else (OUTPUT_ROOT / OUTPUT_DIRNAME)
    manifest = _json(out / "manifest.json")
    with (out / "cleveland-attended-artifact-queue.csv").open(
            encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with (out / "work-browser-targeted-queue.csv").open(
            encoding="utf-8", newline="") as handle:
        founder = list(csv.DictReader(handle))

    with SEED_PATH.open(encoding="utf-8-sig", newline="") as handle:
        seed_rows = list(csv.DictReader(handle))
    checks = validate(rows, partition=_json(PARTITION_PATH),
                      census=_json(CENSUS_PATH), facts=_json(FACTS_PATH),
                      exclusions=_json(EXCLUSIONS_PATH), seed_rows=seed_rows,
                      dayton_census=(_json(DAYTON_CENSUS_PATH)
                                     if DAYTON_CENSUS_PATH.exists() else None),
                      output_dir=out,
                      input_hashes=manifest["input_files_sha256"])
    checks.append(_check(
        "both_csvs_carry_the_same_rows_in_the_same_order",
        [r["queue_id"] for r in rows] == [r["queue_id"] for r in founder],
        "%d machine rows, %d founder rows" % (len(rows), len(founder))))
    checks.append(_check(
        "queue_totals_equal_manifest_totals",
        manifest["queue_totals"]["total"] == len(rows)
        and all(manifest["queue_totals"][k]
                == sum(1 for r in rows if r["queue_class"] == k)
                for k in QUEUE_ORDER),
        "manifest=%s" % dict(manifest["queue_totals"])))
    checks.append(_check(
        "manifest_input_hashes_still_match_the_files_on_disk",
        all(sha256_file(_REPO_ROOT / label) == value
            for label, value in manifest["input_files_sha256"].items()
            if (_REPO_ROOT / label).exists()),
        "re-hashed every input the manifest names that exists in this clone"))
    return {"checks": checks, "rows": rows, "manifest": manifest}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="write the package (default: report only)")
    parser.add_argument("--validate", action="store_true",
                        help="re-validate the package already on disk")
    parser.add_argument("--package-dir", default=None,
                        help="the 27-file operator browser package")
    parser.add_argument("--output-dir", default=None,
                        help="the evidence root to create")
    args = parser.parse_args(list(argv) if argv is not None else None)

    out = Path(args.output_dir) if args.output_dir else (OUTPUT_ROOT / OUTPUT_DIRNAME)

    if args.validate:
        result = validate_on_disk(out)
        for check in result["checks"]:
            print("%-6s %s -- %s"
                  % ("PASS" if check["passed"] else "FAIL",
                     check["check"], check["detail"]))
        return 0 if all(c["passed"] for c in result["checks"]) else 1

    pkg = Path(args.package_dir) if args.package_dir else PACKAGE_DIR
    if not input_present(pkg):
        print("operator package not present: %s" % pkg)
        return 2

    if not args.apply:
        state = build(package_dir=pkg, output_dir=out)
        rows = state["rows"]
        for klass in QUEUE_ORDER:
            members = [r for r in rows if r["queue_class"] == klass]
            print("Queue %s (%s): %d" % (klass, QUEUE_LABELS[klass], len(members)))
        print("total %d -- rerun with --apply to write %s" % (len(rows), out))
        return 0

    state = write(package_dir=pkg, output_dir=out)
    for check in state["checks"]:
        print("%-6s %s -- %s"
              % ("PASS" if check["passed"] else "FAIL",
                 check["check"], check["detail"]))
    print("wrote %d rows to %s" % (len(state["rows"]), out))
    return 0 if all(c["passed"] for c in state["checks"]) else 1


if __name__ == "__main__":            # pragma: no cover
    raise SystemExit(main())
