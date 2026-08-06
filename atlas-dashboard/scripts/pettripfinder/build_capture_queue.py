"""PTF-CAPTURE-003 -- build a capture queue from the PetTripFinder seed.

Hand-authoring queues does not scale and it hides gaps. The Hilton Columbus at
Easton entry in the first pilot had to have its street address recovered from a
*built HTML bundle*, because nothing in the queue-authoring path read the seed.
This script closes that: the seed is the single source of identity, and a hotel
that the seed cannot fully describe is excluded with a reason rather than
guessed at.

It DERIVES nothing it can borrow:

  * ``listing_key``  -- ``site_data.normalize_name``, the same function that
    keys the published launch package (verified 33/33 against it).
  * URL shape, property code -- ``source_retrieval``, the same functions the
    ingestion gate applies.
  * entry validity -- ``capture_automation.queue.validate_entry``, the real
    preflight. There is no second, looser definition of "valid queue entry"
    living here.

Read-only with respect to everything that matters: it reads the seed CSV, the
launch package and the retrieval artifacts, and writes one queue file. It never
attests, approves, promotes, captures or deploys.

WHAT ``--status`` MEANS, EXACTLY
--------------------------------
``status`` here is **publication state only**. It is computed by comparing the
row's ``listing_key`` against the keys in the committed launch package
(``launch_packages/pettripfinder/hotel_policy_facts.json``):

  ``published``    the hotel IS in the current published launch package
  ``unpublished``  the hotel is in the seed but is NOT in that package
  ``any``          either (the default)

It is deliberately NOT any of the following, and must not be reinterpreted as
them by a later change:

  * evidence status -- whether a hotel has backed evidence or is pending
  * capture-worthiness -- whether a capture would succeed or is needed
  * attestation or approval state -- those live in the attestation records and
    are never consulted here
  * renderability -- the ``listing_readiness`` boundary is a separate concept

A hotel can be ``published`` and still need a fresh capture, and a hotel can be
``unpublished`` for reasons that have nothing to do with evidence. Conflating
publication with evidence would let this selector quietly become a
capture-worthiness judgement, which is a decision the attestation pipeline
owns and this script must not make.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.site_data import (            # noqa: E402
    PRODUCTION_CSV, normalize_name,
)
from scripts.pettripfinder.hotel_exclusions import (   # noqa: E402
    exclusion_for, load_exclusions,
)
from services.research_workers import vocabulary as V    # noqa: E402
from services.research_workers.capture_automation.adapters import (  # noqa: E402
    known_brands,
)
from services.research_workers.capture_automation.queue import (     # noqa: E402
    QUEUE_SCHEMA, validate_entry,
)

HOTEL_CATEGORY = "pet-friendly-hotels"
LAUNCH_PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"
RETRIEVAL_ROOT = REPO_ROOT / "data" / "worker_runs" / "pettripfinder"

# Publication state, and nothing else. See the module docstring: this is a
# comparison against the committed launch package's keys, never a judgement
# about evidence, capture-worthiness or approval.
STATUS_PUBLISHED = "published"        # in hotel_policy_facts.json
STATUS_UNPUBLISHED = "unpublished"    # in the seed, absent from that package
STATUS_ANY = "any"                    # either
STATUSES = (STATUS_PUBLISHED, STATUS_UNPUBLISHED, STATUS_ANY)

#: Registrable domain -> brand slug. Only brands with an adapter can actually
#: be queued; the rest are recognised purely so the exclusion reason can say
#: which brand is unsupported instead of "unknown".
BRAND_DOMAINS = (
    ("marriott.com", "marriott"),
    ("hilton.com", "hilton"),
    ("ihg.com", "ihg"),
    ("hyatt.com", "hyatt"),
    ("wyndhamhotels.com", "wyndham"),
    ("druryhotels.com", "drury"),
    ("sonesta.com", "sonesta"),
    ("redroof.com", "redroof"),
    ("extendedstayamerica.com", "extendedstay"),
    ("choicehotels.com", "choice"),
    ("bestwestern.com", "bestwestern"),
)


def brand_for_url(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    for domain, slug in BRAND_DOMAINS:
        if host == domain or host.endswith("." + domain):
            return slug
    return ""


def hotel_id_for(name: str) -> str:
    """Filename-safe unique id. Hyphenated because it names files and journal
    records; ``listing_key`` stays in the pipeline's space-separated form."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", (name or "").lower())).strip("-")


# --------------------------------------------------------------------------- #
# Inputs.
# --------------------------------------------------------------------------- #

def read_seed_hotels(csv_path: pathlib.Path = None) -> List[Dict[str, str]]:
    """Hotel rows from the production seed. Read-only."""
    path = pathlib.Path(csv_path) if csv_path else PRODUCTION_CSV
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("category") or "") == HOTEL_CATEGORY]


def published_keys(package_path: pathlib.Path = None) -> frozenset:
    """listing_keys already in the published launch package."""
    path = pathlib.Path(package_path) if package_path else LAUNCH_PACKAGE
    if not path.exists():
        return frozenset()
    try:
        pkg = json.loads(path.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return frozenset()
    return frozenset(str(h.get("key") or "") for h in pkg.get("hotels") or [])


def retrieval_artifacts(root: pathlib.Path = None) -> Dict[str, str]:
    """``hotel_id -> artifact path`` for every ``retr-<id>.json`` on disk.

    Gate 1 refuses any attestation with no demonstrated automated failure, so a
    hotel with no retrieval artifact is work that could never be published --
    better excluded here than captured and stranded.
    """
    base = pathlib.Path(root) if root else RETRIEVAL_ROOT
    found: Dict[str, str] = {}
    if not base.exists():
        return found
    for path in sorted(base.rglob("retr-*.json")):
        found.setdefault(path.stem[len("retr-"):], str(path))
    return found


# --------------------------------------------------------------------------- #
# Selection + build.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Excluded:
    hotel_id: str
    name: str
    reason: str

    def to_dict(self) -> dict:
        return {"hotel_id": self.hotel_id, "name": self.name, "reason": self.reason}


@dataclass(frozen=True)
class BuildResult:
    queue: dict
    selected: Tuple[dict, ...]
    excluded: Tuple[Excluded, ...]
    output_path: Optional[pathlib.Path] = None
    #: True when --limit stopped the scan early, which makes ``excluded``
    #: a partial list. Reported so the summary is never misread as "these are
    #: all the problems in the seed".
    limit_reached: bool = False
    scanned: int = 0

    @property
    def counts(self) -> dict:
        return {"seed_hotels_scanned": self.scanned,
                "selected": len(self.selected), "excluded": len(self.excluded),
                "scan_truncated_by_limit": self.limit_reached}


def _matches_filters(row: dict, hotel_id: str, brand: str, *,
                     markets: Sequence[str], brands: Sequence[str],
                     status: str, hotel_ids: Sequence[str],
                     published: frozenset, listing_key: str) -> str:
    """Return "" when the row is wanted, else a skip reason.

    Filter misses are recorded separately from validation failures: "you did not
    ask for this hotel" and "this hotel cannot be captured" are different facts
    and conflating them makes the summary useless.
    """
    if hotel_ids and hotel_id not in hotel_ids:
        return "filtered_out:hotel_id"
    if markets:
        city = (row.get("city") or "").strip().lower()
        if city not in [m.lower() for m in markets]:
            return "filtered_out:market"
    if brands and brand not in [b.lower() for b in brands]:
        return "filtered_out:brand"
    if status == STATUS_PUBLISHED and listing_key not in published:
        return "filtered_out:status"
    if status == STATUS_UNPUBLISHED and listing_key in published:
        return "filtered_out:status"
    return ""


def build_queue(*, batch_id: str, created_at: str = "",
                markets: Sequence[str] = (), brands: Sequence[str] = (),
                status: str = STATUS_ANY, hotel_ids: Sequence[str] = (),
                limit: int = 0, require_retrieval_artifact: bool = True,
                seed_csv=None, package_path=None, retrieval_root=None,
                include_filtered_in_report: bool = False,
                exclusions_path=None, revalidate_excluded: bool = False) -> BuildResult:
    """Select seed hotels and build a validated ``ptf-capture-queue/1.0``.

    ``revalidate_excluded`` is the explicit revalidation workflow: it is the
    ONLY way an excluded identity re-enters a capture queue, and it must be
    asked for deliberately.
    """
    rows = read_seed_hotels(seed_csv)
    published = published_keys(package_path)
    exclusion_records = [] if revalidate_excluded else load_exclusions(exclusions_path)
    artifacts = retrieval_artifacts(retrieval_root)
    adapters = frozenset(known_brands())

    selected: List[dict] = []
    excluded: List[Excluded] = []
    seen_urls: Dict[str, str] = {}
    limit_reached = False
    scanned = 0

    for row in rows:
        scanned += 1
        name = (row.get("name") or "").strip()
        hotel_id = hotel_id_for(name)
        listing_key = normalize_name(name)
        url = (row.get("website_url") or "").strip()
        brand = brand_for_url(url)

        skip = _matches_filters(row, hotel_id, brand, markets=markets, brands=brands,
                                status=status, hotel_ids=hotel_ids,
                                published=published, listing_key=listing_key)
        if skip:
            if include_filtered_in_report:
                excluded.append(Excluded(hotel_id, name, skip))
            continue

        # PTF-EXCLUSIONS: an identity already answered by evidence -- its own
        # official page says no pets, or it is closed, duplicated or out of
        # market -- is not capture-worthy. Re-reading the same sentence every
        # sweep is wasted operator time. A merely UNVERIFIED hold is not an
        # exclusion and never reaches this check.
        excl = exclusion_for(name, row.get("address", ""), row.get("postal_code", ""),
                             records=exclusion_records)
        if excl is not None:
            excluded.append(Excluded(hotel_id, name,
                                     "excluded_identity:%s" % excl["exclusion_state"]))
            continue

        # -- fail-closed checks the queue contract cannot see ---------------- #
        if not brand:
            excluded.append(Excluded(hotel_id, name, "brand_unrecognised:%s"
                                     % (urlsplit(url).hostname or "no-host")))
            continue
        if brand not in adapters:
            excluded.append(Excluded(hotel_id, name, "no_adapter_for_brand:%s" % brand))
            continue

        # One official URL cannot be property-specific for two properties. The
        # seed is clean today; this costs nothing and stops a future generic
        # brand URL being queued for a dozen hotels at once.
        if url in seen_urls:
            excluded.append(Excluded(hotel_id, name,
                                     "official_url_not_unique:shared_with:%s" % seen_urls[url]))
            continue

        artifact = artifacts.get(hotel_id, "")
        if require_retrieval_artifact and not artifact:
            excluded.append(Excluded(hotel_id, name, "retrieval_artifact_missing"))
            continue

        raw = {
            "hotel_id": hotel_id,
            "listing_key": listing_key,
            "hotel_name": name,
            "brand": brand,
            "official_url": url,
            "expected_address": (row.get("address") or "").strip(),
            "expected_city": (row.get("city") or "").strip(),
            "expected_state": (row.get("state") or "").strip(),
            "expected_postal_code": (row.get("postal_code") or "").strip(),
            "expected_phone": (row.get("phone") or "").strip(),
            "expected_property_code": _property_code(url),
            "required_fields": list(V.POLICY_FIELDS),
            # FD-3 rule 2: the worker owns this value; the producer reads and
            # propagates it. Emitting it explicitly makes the contract the
            # queue was built against auditable from the file itself rather
            # than inferred from whenever it happens to be loaded.
            "worker_contract_version": V.CONTRACT_VERSION,
            "retrieval_artifact": artifact,
            "notes": "generated from %s" % (pathlib.Path(seed_csv).name if seed_csv
                                            else PRODUCTION_CSV.name),
        }

        # The real preflight decides. No second definition of validity here.
        entry, problems = validate_entry(raw, len(selected), known_brands=tuple(adapters))
        if entry is None:
            reason = "; ".join(p.split(": ", 1)[-1] for p in problems)
            excluded.append(Excluded(hotel_id, name, reason))
            continue

        seen_urls[url] = hotel_id
        selected.append(raw)
        if limit and len(selected) >= limit:
            limit_reached = scanned < len(rows)
            break

    queue = {"schema": QUEUE_SCHEMA, "batch_id": batch_id,
             "created_at": created_at, "hotels": selected}
    return BuildResult(queue=queue, selected=tuple(selected), excluded=tuple(excluded),
                       limit_reached=limit_reached, scanned=scanned)


def _property_code(url: str) -> str:
    from services.research_workers.source_retrieval import extract_property_code_from_url
    return extract_property_code_from_url(url)


# --------------------------------------------------------------------------- #
# Reporting + CLI.
# --------------------------------------------------------------------------- #

def format_summary(result: BuildResult, *, output_path=None, wrote: bool = False) -> str:
    lines: List[str] = []
    c = result.counts
    lines.append("selected %d hotel(s), excluded %d (scanned %d of the seed)"
                 % (c["selected"], c["excluded"], result.scanned))
    if result.limit_reached:
        lines.append("NOTE: --limit stopped the scan early; the excluded list "
                     "below is partial, not a full audit of the seed.")
    if result.selected:
        lines.append("")
        lines.append("SELECTED:")
        for h in result.selected:
            lines.append("  %-40s %-9s %s" % (h["hotel_id"][:40], h["brand"],
                                              h["expected_property_code"]))
    if result.excluded:
        grouped: Dict[str, List[str]] = {}
        for e in result.excluded:
            grouped.setdefault(e.reason.split(":")[0], []).append(e.name)
        lines.append("")
        lines.append("EXCLUDED:")
        for e in result.excluded:
            lines.append("  %-40s %s" % (e.name[:40], e.reason))
        lines.append("")
        lines.append("  by reason: " + ", ".join(
            "%s=%d" % (k, len(v)) for k, v in sorted(grouped.items())))
    lines.append("")
    if output_path is not None:
        lines.append("%s: %s" % ("wrote" if wrote else "would write", output_path))
    return "\n".join(lines)


def _cmd_validate_only(path: pathlib.Path) -> int:
    """Re-run the real preflight against an existing queue file."""
    from services.research_workers.capture_automation.queue import QueueError, load_queue
    try:
        queue = load_queue(path, known_brands=known_brands())
    except QueueError as exc:
        sys.stderr.write("queue INVALID:\n%s\n" % exc)
        return 2
    print("queue VALID: %d hotel(s), batch_id=%s" % (len(queue), queue.batch_id))
    for e in queue.entries:
        print("  %-40s %-9s %s" % (e.hotel_id[:40], e.brand, e.expected_property_code))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PTF-CAPTURE-003 -- generate a ptf-capture-queue/1.0 file from "
                    "the PetTripFinder seed. Never attests, approves, promotes or "
                    "deploys.")
    p.add_argument("--batch-id", default="", help="queue batch id (required unless --validate-only)")
    p.add_argument("--output", default="", help="queue file to write")
    p.add_argument("--market", action="append", default=[], help="city; repeatable")
    p.add_argument("--brand", action="append", default=[], help="brand slug; repeatable")
    p.add_argument("--status", choices=STATUSES, default=STATUS_ANY,
                   help="PUBLICATION STATE ONLY, computed against the committed "
                        "launch package: 'published' = the hotel IS in "
                        "launch_packages/pettripfinder/hotel_policy_facts.json; "
                        "'unpublished' = in the seed but NOT in that package; "
                        "'any' = either (default). This is NOT evidence status, "
                        "NOT capture-worthiness, and NOT attestation or approval "
                        "state -- a published hotel may still need a fresh "
                        "capture.")
    p.add_argument("--hotel-id", action="append", default=[], help="explicit hotel id; repeatable")
    p.add_argument("--limit", type=int, default=0, help="stop after N selected hotels")
    p.add_argument("--created-at", default="", help="ISO timestamp recorded in the queue")
    p.add_argument("--allow-missing-retrieval-artifact", action="store_true",
                   help="permit entries with no Gate-1 artifact (they cannot be "
                        "attested later; off by default)")
    p.add_argument("--show-filtered", action="store_true",
                   help="also report hotels skipped by the filters, not just failures")
    p.add_argument("--dry-run", action="store_true", help="build and report; write nothing")
    p.add_argument("--validate-only", default="",
                   help="path of an existing queue file to validate; builds nothing")
    p.add_argument("--json", action="store_true", help="emit the summary as JSON")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.validate_only:
        return _cmd_validate_only(pathlib.Path(args.validate_only))

    if not args.batch_id:
        sys.stderr.write("--batch-id is required (or use --validate-only)\n")
        return 2
    if not args.output and not args.dry_run:
        sys.stderr.write("--output is required unless --dry-run\n")
        return 2

    result = build_queue(
        batch_id=args.batch_id, created_at=args.created_at,
        markets=args.market, brands=args.brand, status=args.status,
        hotel_ids=args.hotel_id, limit=args.limit,
        require_retrieval_artifact=not args.allow_missing_retrieval_artifact,
        include_filtered_in_report=args.show_filtered)

    out = pathlib.Path(args.output) if args.output else None
    wrote = False
    if out is not None and not args.dry_run:
        if not result.selected:
            sys.stderr.write("refusing to write an empty queue\n")
            print(format_summary(result, output_path=out, wrote=False))
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.queue, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        wrote = True

    if args.json:
        print(json.dumps({"counts": result.counts,
                          "selected": [h["hotel_id"] for h in result.selected],
                          "excluded": [e.to_dict() for e in result.excluded],
                          "output_path": str(out) if out else "",
                          "wrote": wrote}, indent=2, ensure_ascii=False))
    else:
        print(format_summary(result, output_path=out, wrote=wrote))
    return 0 if result.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
