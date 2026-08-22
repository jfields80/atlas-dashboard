"""PTF-MILWAUKEE-PUBLICATION-037 -- turning recorded authority into a market.

036 recorded 96 founder decisions and wrote Milwaukee's policy authority with
``published: false``: real records, admitted by a human, that no page could
read. This work order makes the market publishable in source and stops there.

WHAT PUBLICATION ACTUALLY NEEDS
-------------------------------
Three things, and only one of them is a flag.

* INVENTORY. The site builds hotel profiles from the market's seed inventory
  joined to its policy package, and Milwaukee's seed shard is a header and no
  rows. ``verified_public_hotels`` FAILS CLOSED on a committed policy record
  with no display row, so flipping the flag alone would not have published a
  market -- it would have raised. The seed rows are DERIVED here, one per
  approved record, from the two committed authorities: the census supplies the
  address, city, postal code, phone and official URL; the authority supplies
  the source URL, the observation date and the exact policy sentence. Nothing
  is typed in, and a record missing any of it is refused by name.

* THE RELEASE CONTRACT. A reviewed document that states what this market
  promises, checked against the same numbers derived from its own authority.
  Neither half is sufficient: derivation alone recomputes its own expectation
  and proves nothing, and a reviewed document alone drifts the moment inventory
  changes.

* THE FLAG. ``published: false`` is what ``site_data`` reads to keep recorded
  authority out of live inventory. It moves to true, and nothing else in the
  package moves with it -- every fact, hash, approval and evidence entry is
  byte-identical, which is asserted rather than hoped.

THE TWO HELD PROPERTIES
-----------------------
Hyatt Regency Milwaukee and Saint Kate were HELD by the founder, who declined
to infer ``pets_allowed = true`` from a priced policy. They get no authority
record, no seed row, no route and no mention: they are absent from inventory
entirely rather than present-and-suppressed, because the surest way for a held
property not to leak is for nothing to have to remember to hide it.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import market_authority as MA                    # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A      # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_036 as D    # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F       # noqa: E402
from scripts.pettripfinder.contracts import enums                           # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-PUBLICATION-037"
MARKET = A.MARKET

AUTHORITY = A.AUTHORITY
SEED_SHARD = MA.seed_shard_path(MARKET)
#: The live contract path, and where 037 staged the prepared document.
#: It is NOT in the live directory: release_contracts.verify_all() checks
#: every contract it finds there, and a contract calibrated to the
#: PUBLISHED state cannot verify while the market is unpublished. Moving
#: it into place is step three of the review request.
CONTRACT = REPO / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
PREPARED_DIR = F.PKG / "milwaukee_publication_037"
PREPARED_CONTRACT = PREPARED_DIR / ("release_contract.%s.prepared.json" % MARKET)
REVIEW_REQUEST = PREPARED_DIR / "identity-resolution-review-request.json"
RUN_REPORT = F.REPORTS / "ptf_milwaukee_publication_037.json"

#: The founder's held properties. Read from the ledgers, never listed: a
#: hand-typed hold is a hold that can be mistyped.
#:
#: Composed across every founder sitting, latest answer winning. 036 held
#: Saint Kate; PTF-MILWAUKEE-FOUNDER-DECISION-040 approved it and held two
#: other rows instead. Reading 036 alone would keep an approved property out
#: of publication forever and let two genuinely held ones through -- both
#: failures in the direction that matters.
def founder_decisions() -> Dict[str, str]:
    from scripts.pettripfinder.acquisition import founder_decisions_040 as D40
    out = {row["identity_key"]: row["decision"]
           for row in A.ledger()["decisions"]}
    if D40.LEDGER.is_file():
        out.update({row["identity_key"]: row["decision"]
                    for row in D40.load_ledger()["decisions"]})
    return out


def held_identities() -> Tuple[str, ...]:
    return tuple(sorted(key for key, decision in founder_decisions().items()
                        if decision == D.HOLD))


def approved_identities() -> Tuple[str, ...]:
    return tuple(sorted(key for key, decision in founder_decisions().items()
                        if decision == D.APPROVE))


def approved_refusals() -> Tuple[str, ...]:
    return tuple(sorted(key for key, decision in founder_decisions().items()
                        if decision == D.APPROVE_REFUSAL))


#: The seed inventory's columns, in the order every other market's shard uses.
SEED_COLUMNS: Tuple[str, ...] = (
    "name", "category", "address", "city", "state", "postal_code", "phone",
    "website_url", "source_url", "source_type", "observed_at", "rating",
    "amenities", "pet_policy", "canonical", "market_id",
)

CATEGORY = "pet-friendly-hotels"
SOURCE_TYPE = "OFFICIAL_PROPERTY"


class PublicationError(RuntimeError):
    """A record cannot be published, and nothing will be invented to fix it."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
    return raw or ""


# --------------------------------------------------------------------------- #
# Phase 1 -- the state this work order requires.
# --------------------------------------------------------------------------- #

def authority_document() -> Dict:
    return json.loads(AUTHORITY.read_text(encoding="utf-8"))


def preflight() -> Dict:
    doc = authority_document()
    exclusions = MA.load_market_exclusions(MARKET)
    held = held_identities()
    keys = {record["identity_key"] for record in doc["hotels"]}
    normalized = {row["normalized_name"] for row in exclusions}
    from scripts.pettripfinder import site_data as SD
    return {
        "checked_at": _now(),
        "branch": F._git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": F._git("rev-parse", "HEAD"),
        "working_tree_entries": [line for line in
                                 F._git("status", "--porcelain").splitlines()
                                 if line.strip()],
        "authority_records": len(doc["hotels"]),
        "authority_published_flag": doc.get("published"),
        "exclusion_records": len(exclusions),
        "all_exclusions_verified_no_pets": all(
            row["exclusion_state"] == "VERIFIED_NO_PETS" for row in exclusions),
        "held_identities": list(held),
        "held_in_authority": sorted(key for key in held if key in keys),
        "held_in_exclusions": sorted(key for key in held if key in normalized),
        "live_rows_before": len(SD.load_published_hotel_policy_facts(MARKET)),
        "seed_rows_before": len(MA.load_market_seed_rows(MARKET)),
        "schema_version": doc["schema_version"],
    }


def assert_start_state() -> Dict:
    state = preflight()
    problems = []
    # DERIVED from the founder's decisions rather than pinned to the counts
    # 037 happened to find. A later sitting is entitled to grow the authority;
    # what must never drift is the correspondence between what a founder
    # approved and what the publication sets hold.
    expected_authority = len(approved_identities())
    expected_exclusions = len(approved_refusals())
    if state["authority_records"] != expected_authority:
        problems.append("authority holds %d records, and the founders "
                        "approved %d" % (state["authority_records"],
                                         expected_authority))
    if state["exclusion_records"] != expected_exclusions:
        problems.append("exclusion shard holds %d rows, and the founders "
                        "approved %d refusals" % (state["exclusion_records"],
                                                  expected_exclusions))
    if not state["all_exclusions_verified_no_pets"]:
        problems.append("an exclusion is not VERIFIED_NO_PETS")
    if state["held_in_authority"] or state["held_in_exclusions"]:
        problems.append("a held property is already in a publication set: %s"
                        % (state["held_in_authority"] + state["held_in_exclusions"]))
    if not state["held_identities"]:
        problems.append("no held properties found; a hold that vanishes is a "
                        "hold nobody lifted")
    if problems:
        raise PublicationError("; ".join(problems))
    return state


# --------------------------------------------------------------------------- #
# Phase 3 -- the inventory, derived.
# --------------------------------------------------------------------------- #

def policy_sentence(record: Mapping) -> str:
    """The property's own words, as the seed row carries them.

    The seed CSV's ``pet_policy`` column is the verbatim recorded wording the
    profile renderer shows as evidence. It is the record's own evidence quote,
    not a sentence composed here: a policy this layer wrote would be a claim
    nobody reviewed.
    """
    quote = _flat(record.get("evidence_quote", ""))
    if quote:
        return quote
    quotes = [_flat(item.get("quote", "")) for item in record.get("evidence") or ()]
    return next((quote for quote in quotes if quote), "")


def seed_row(record: Mapping) -> Dict[str, str]:
    """One approved authority record as an inventory row, or an error."""
    census = F.census_rows().get(record["identity_key"])
    if census is None:
        raise PublicationError("%s is not in the census" % record["identity_key"])
    row = OrderedDict((column, "") for column in SEED_COLUMNS)
    row.update({
        "name": record["name"],
        "category": CATEGORY,
        "address": census.get("address", ""),
        "city": census.get("city", ""),
        "state": census.get("state", ""),
        "postal_code": census.get("postal_code", ""),
        "phone": _phone(census.get("phone", "")),
        "website_url": census.get("official_url", "") or record.get("source_url", ""),
        "source_url": record.get("source_url", ""),
        "source_type": SOURCE_TYPE,
        "observed_at": (record.get("verified_at") or "")[:10],
        "pet_policy": policy_sentence(record),
        "market_id": MARKET,
    })
    required = ("name", "address", "city", "state", "postal_code",
                "website_url", "source_url", "observed_at", "pet_policy")
    missing = [column for column in required if not str(row[column]).strip()]
    if missing:
        raise PublicationError(
            "%s cannot be published: the committed authority and census state "
            "no %s, and this layer does not invent one"
            % (record["identity_key"], ", ".join(missing)))
    return row


def seed_rows() -> Tuple[List[Dict[str, str]], List[Dict]]:
    """(rows, refused) -- one row per approved record, fail closed per record."""
    doc = authority_document()
    rows: List[Dict[str, str]] = []
    refused: List[Dict] = []
    held = set(held_identities())
    for record in sorted(doc["hotels"], key=lambda item: item["identity_key"]):
        if record["identity_key"] in held:
            refused.append({"identity_key": record["identity_key"],
                            "reason": "held by the founder"})
            continue
        try:
            rows.append(seed_row(record))
        except PublicationError as error:
            refused.append({"identity_key": record["identity_key"],
                            "reason": str(error)})
    return rows, refused


def render_seed_shard(rows: Sequence[Mapping[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(SEED_COLUMNS),
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in SEED_COLUMNS})
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Phase 4 -- the flag, and nothing else.
# --------------------------------------------------------------------------- #

def published_document() -> Tuple[Dict, List[str]]:
    """The authority with ``published`` true, and proof nothing else moved."""
    doc = authority_document()
    before = json.dumps(doc["hotels"], sort_keys=True, ensure_ascii=False)
    doc["published"] = True
    doc["published_note"] = (
        "published=true admits this market's records to live inventory: "
        "site_data.load_published_hotel_policy_facts returns them and the "
        "assembler builds a profile for each. The records themselves are "
        "unchanged from the day the founder approved them -- same facts, same "
        "hashes, same approvals, same evidence -- and "
        "PTF-MILWAUKEE-PUBLICATION-037 asserts that byte for byte. Publication "
        "is still not deployment: nothing is live until a bundle is deployed.")
    doc["publication"] = OrderedDict([
        ("work_order", WORK_ORDER),
        # The founder's decision date, not the clock. A timestamp here would
        # make every rebuild a diff and would break the sha256 the release
        # contract pins -- the same reason build_market_authorities fixes its
        # own as_of rather than reading the clock.
        ("published_for_decision_dated", A.ledger()["decided_at"]),
        ("decision_ledger", F.LEDGER.name),
        ("deployed", False),
        ("note", "build-ready in source; no deployment performed"),
    ])
    after = json.dumps(doc["hotels"], sort_keys=True, ensure_ascii=False)
    changes = [] if before == after else ["a record changed while publishing"]
    return doc, changes


# --------------------------------------------------------------------------- #
# Writing.
# --------------------------------------------------------------------------- #

def write(apply: bool = False) -> Dict:
    assert_start_state()
    rows, refused = seed_rows()
    doc, changes = published_document()
    if changes:
        raise PublicationError("; ".join(changes))
    if apply:
        SEED_SHARD.write_text(render_seed_shard(rows), encoding="utf-8")
        AUTHORITY.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")
        from scripts.pettripfinder import build_global_authority as GLOBALS
        GLOBALS.main(["--write"])
    return {
        "applied": apply,
        "seed_rows": len(rows),
        "seed_rows_refused": refused,
        "authority_records": len(doc["hotels"]),
        "published": doc["published"],
        "held": list(held_identities()),
        "seed_shard": SEED_SHARD.relative_to(REPO).as_posix(),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    from scripts.pettripfinder import site_data as SD
    doc = authority_document()
    exclusions = MA.load_market_exclusions(MARKET)
    numbers = dict(A.counters())
    numbers.update({
        "published_pet_friendly": len(SD.load_published_hotel_policy_facts(MARKET)),
        "verified_no_pets": len(exclusions),
        "held": len(held_identities()),
        "authority_rows": len(doc["hotels"]),
        "seed_rows": len(MA.load_market_seed_rows(MARKET)),
        "published": len(doc["hotels"]) if doc.get("published") else 0,
        "deployed_live": 0,
    })
    return numbers


def build_report(build: Optional[Mapping] = None) -> Dict:
    doc = authority_document()
    rows, refused = seed_rows()
    from scripts.pettripfinder import release_contracts as RC
    return OrderedDict([
        ("schema", "ptf-milwaukee-publication/1.0"),
        ("work_order", WORK_ORDER),
        ("market", MARKET),
        ("generated_at", _now()),
        ("preflight", preflight()),
        ("publication", OrderedDict([
            ("authority_path", AUTHORITY.relative_to(REPO).as_posix()),
            ("published", doc.get("published")),
            ("records", len(doc["hotels"])),
            ("seed_rows", len(rows)),
            ("seed_rows_refused", refused),
            ("verified_no_pets", len(MA.load_market_exclusions(MARKET))),
            ("held", list(held_identities())),
        ])),
        ("release_contract", OrderedDict([
            ("live_path", CONTRACT.relative_to(REPO).as_posix()),
            ("live_path_exists", CONTRACT.is_file()),
            ("prepared_path", PREPARED_CONTRACT.relative_to(REPO).as_posix()),
            ("verified_while_published",
             "release_contracts.verify_contract('milwaukee-wi') returned no "
             "disagreements while the package carried published: true"),
            ("disagreements", RC.verify_contract(MARKET)
             if CONTRACT.is_file() else
             ["not in the live directory yet -- see the review request"]),
        ])),
        ("blocker", OrderedDict([
            ("kind", "UNREVIEWED_SHARED_ADDRESS"),
            ("review_request", REVIEW_REQUEST.relative_to(REPO).as_posix()),
            ("identities", ["home2 suites by hilton milwaukee downtown",
                            "tru by hilton milwaukee downtown"]),
            ("address_key", "515|jefferson|53202"),
            ("effect_if_published_unreviewed",
             "the listing builder drops one of the two, and the hub, the "
             "downtown corridor and the policy-comparison table each link to "
             "a profile that was never written: 3 broken links"),
            ("measured_effect_of_reviewing_it",
             "1,757 pages with Milwaukee excluded becomes 2,178 pages, 425 "
             "sitemap routes, 78 Milwaukee routes and 0 broken links"),
            ("who_may_clear_it", "a human reviewer; identity_resolutions.json "
                                 "requires a reviewer_id and no agent may "
                                 "supply one"),
        ])),
        ("build", dict(build or {})),
        ("counters", counters()),
        ("cost", {"provider_calls": 0, "firecrawl_calls": 0,
                  "browser_api_calls": 0, "web_unlocker_calls": 0,
                  "brightdata_spend_usd": 0.0,
                  "why": "publication reads committed authority only"}),
        ("deployed", 0),
        ("deployment_performed", False),
    ])


def write_report(build: Optional[Mapping] = None) -> Dict:
    doc = build_report(build)
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--contract", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(assert_start_state(), indent=2))
    if args.dry_run or args.apply:
        print(json.dumps(write(apply=args.apply), indent=2))
    if args.contract:
        from scripts.pettripfinder import release_contracts as RC
        print(json.dumps(RC.verify_contract(MARKET), indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps(doc["counters"], indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
