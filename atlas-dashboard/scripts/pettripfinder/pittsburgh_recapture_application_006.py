# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-IDENTITY-AND-RECAPTURE-006 Phase 10 -- apply the three approved rulings.

    python -m scripts.pettripfinder.pittsburgh_recapture_application_006
    python -m scripts.pettripfinder.pittsburgh_recapture_application_006 --write

THREE ROWS, AND ONLY THREE
----------------------------
The founder approved exactly these:

  springhill suites pittsburgh airport              VERIFIED_NO_PETS
  holiday inn express and suites pittsburgh airport  VERIFIED_NO_PETS
  embassy suites by hilton pittsburgh downtown       PUBLISHED_PET_FRIENDLY (fee basis ABSENT)

The three identity rulings put to the founder in the same packet -- the Courtyard
West Homestead supersession, the Comfort Suites canonical-name adoption, and the
InTown Suites census add -- were NOT authorised. They are not applied, the census
stays at 101, and those rows keep their holds.

SPRINGHILL: A LABEL WAS READ AS A VALUE
-----------------------------------------
The live page, captured free on attended Chrome, carries all three statements in
ONE Pet Policy panel:

    Pet Policy | Pets Welcome | Pets are not allowed. Only service animals are
    welcome | Non-Refundable Pet Fee Per Stay: $150.00

``"hws.petsAllowed":"Pets Welcome"`` is in Marriott's own translation bundle, so
"Pets Welcome" is a SECTION HEADER rendered for every property -- and it is the
exact string PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 cited as its evidence
for ``pets_allowed = true``. That is the label-vs-value boundary defect
(PTF-DEFECT-LABEL-VALUE-FIELD-BOUNDARY-001) reaching production.

Marriott also ships ``hws.faq.overview.pets.conversational.no`` -- its FAQ can
say "no". It said "yes" because the fee field is populated. So both affirmative
signals are template artifacts and the only property-authored sentence is a
plain refusal. The founder ruled VERIFIED_NO_PETS on that reading.

EVIDENCE GRADE, STATED PLAINLY
--------------------------------
SpringHill's artifact is an attended-Chrome capture: the SHA-256 is over the
page's rendered outerHTML and every quote was taken in the SAME JavaScript call,
which is the contract. Raw bytes are deliberately not retained -- the live page
mutated 698 bytes between two calls one second apart, so bytes fetched
separately would not match the digest.

The other two come from DECLINED capture directories whose bytes this market
kept but whose hash the acquisition journal never recorded. Their digests are
computed here from the retained bytes and bound to the record. The founder was
told this and approved publishing on it; the ledger says so rather than
implying a hash that existed at capture time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE                  # noqa: E402
from scripts.pettripfinder import market_authority as MA                  # noqa: E402
from scripts.pettripfinder import policy_migration as PM                  # noqa: E402
from scripts.pettripfinder.contracts import enums                         # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify      # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, PACKAGE, REPORTS, _load, _write)

WORK_ORDER = "PTF-PITTSBURGH-IDENTITY-AND-RECAPTURE-006"
AS_OF = "2026-08-30"
REVIEWER = "PTF-FOUNDER-001"
OPERATOR = "jfields80"
CORPUS = (_REPO_ROOT / "data" / "acquisition"
          / "pittsburgh_pa_factory_recensus_001" / "pass1")
ATTENDED = (_REPO_ROOT / "data" / "acquisition"
            / "pittsburgh_pa_free_recapture_006"
            / "springhill-suites-pittsburgh-airport" / "attended_capture.json")
APPLICATION = REPORTS / "pittsburgh_recapture_application_006.json"
FILLS = REPORTS / "pittsburgh_recapture_006_census_address_fills.json"

#: The founder's rulings, each naming the evidence that earned it.
RULINGS = OrderedDict((
    ("springhill suites pittsburgh airport", OrderedDict((
        ("disposition", "VERIFIED_NO_PETS"),
        ("lane", "FREE_ATTENDED_CHROME"),
        ("quote", "Pets are not allowed. Only service animals are welcome"),
        ("ruling",
         "VERIFIED_NO_PETS. The only property-authored sentence on the live "
         "page is a refusal. The two affirmative signals are proven Marriott "
         "templates: 'Pets Welcome' is the value of the UI translation key "
         "hws.petsAllowed (a header rendered for every property, and the exact "
         "string Pass 4 cited as evidence for pets_allowed=true), and the FAQ "
         "answer is generated from the populated fee field -- Marriott ships a "
         "negative FAQ template too. The $150 line is template residue beside "
         "a refusal, not a price for a permission this property grants."),
    ))),
    ("holiday inn express and suites pittsburgh airport", OrderedDict((
        ("disposition", "VERIFIED_NO_PETS"),
        ("lane", "OWNED_DECLINED_CAPTURE"),
        ("slug", "holiday-inn-express-suites-pittsburgh-airport"),
        ("quote", "No, pets are not allowed at Holiday Inn Express & Suites "
                  "Pittsburgh Airport."),
        ("ruling",
         "VERIFIED_NO_PETS. The page names the property exactly, carries its "
         "property code pitex, and states the refusal in its own words. The "
         "census row's official_url is this page."),
    ))),
    ("embassy suites by hilton pittsburgh downtown", OrderedDict((
        ("disposition", "PUBLISHED_PET_FRIENDLY"),
        ("lane", "OWNED_DECLINED_CAPTURE"),
        ("slug", "embassy-suites-by-hilton-pittsburgh-downtown"),
        ("quote", "Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee"),
        ("ruling",
         "PUBLISHED_PET_FRIENDLY. The page states the permission and a $75 "
         "non-refundable fee but never says whether it is per night or per "
         "stay, so the amount publishes and the basis is simply ABSENT -- "
         "silence is absence, not a withholding."),
    ))),
))


class ApplicationError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _owned_page(slug: str) -> Path:
    found = sorted((CORPUS / slug).rglob("rendered.html"))
    if not found:
        raise ApplicationError("no owned page under %s" % slug)
    return found[0]


def _page_field(html: str, pattern: str) -> Optional[str]:
    import re
    found = re.search(pattern, html, re.I)
    return found.group(1).strip() if found else None


def address_fills(census: Dict) -> List[Dict]:
    """Street addresses these three rows need, from their own pages.

    ADD-ONLY, and never over a committed value. Same discipline as the two
    earlier fills: the census row count and schema do not move, so the release
    contract's census pin does not lapse.
    """
    import re
    rows = {h["identity_key"]: h for h in census["hotels"]}
    fills = []
    for key, ruling in RULINGS.items():
        row = rows.get(key)
        if row is None:
            raise ApplicationError("%s is not a registered identity" % key)
        if str(row.get("address") or "").strip():
            continue
        slug = ruling.get("slug")
        if not slug:
            raise ApplicationError("%s has no address and no owned page" % key)
        page = _owned_page(slug)
        html = page.read_text(encoding="utf-8", errors="replace")
        street = _page_field(html, r'"streetAddress"\s*:\s*"([^"]{3,70})"')
        if not street:
            raise ApplicationError("%s: the page states no street address" % key)
        fills.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name")),
            ("address_filled", street),
            ("source", "the identity's own first-party page, JSON-LD streetAddress"),
            ("source_url", row.get("official_url")),
            ("artifact_sha256", "sha256:%s" % _sha(page)),
        )))
    return fills


def _evidence(key: str, ruling: Mapping, census_row: Mapping) -> Tuple[List[Dict], Dict]:
    """(evidence entries, provenance) for one approved row."""
    if ruling["lane"] == "FREE_ATTENDED_CHROME":
        cap = _load(ATTENDED)
        entry = OrderedDict((
            ("field", "pets_allowed"),
            ("quote", ruling["quote"]),
            ("source_url", cap["source_url"]),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", cap["artifact_sha256"]),
            ("artifact_kind", "rendered_html"),
            ("captured_at", cap["captured_at"]),
            ("capture_method", "browser_assisted"),
            ("source_grade", "PT1_FIRST_PARTY"),
        ))
        prov = OrderedDict((("lane", ruling["lane"]), ("provider_calls", 0),
                            ("usd_spent", 0.0),
                            ("digest_contract", cap["digest_contract"])))
    else:
        page = _owned_page(ruling["slug"])
        entry = OrderedDict((
            ("field", "pets_allowed"),
            ("quote", ruling["quote"]),
            ("source_url", census_row.get("official_url")),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", "sha256:%s" % _sha(page)),
            ("artifact_kind", "rendered_html"),
            ("captured_at", "2026-08-23"),
            ("capture_method", "browser_assisted"),
            ("source_grade", "PT1_FIRST_PARTY"),
        ))
        prov = OrderedDict((
            ("lane", ruling["lane"]), ("provider_calls", 0), ("usd_spent", 0.0),
            ("digest_note",
             "This artifact came from a DECLINED capture directory: the bytes "
             "were retained but the acquisition journal recorded no "
             "content_hash at capture time. The digest above is computed here "
             "from those retained bytes. The founder approved publishing on "
             "this evidence with that limitation stated."),
        ))
    entry["evidence_ref"] = PM.evidence_ref_for(entry)
    return [entry], prov


def _caveats(key: str, ruling: Mapping, prov: Mapping) -> List[str]:
    out = [
        "FOUNDER RULING (%s): %s Ruled by %s on %s under %s."
        % (ruling["disposition"], ruling["ruling"], REVIEWER, AS_OF, WORK_ORDER),
        "Zero-cost: provider calls 0, spend $0.00, lane %s." % prov["lane"],
    ]
    if "digest_note" in prov:
        out.append("EVIDENCE GRADE: %s" % prov["digest_note"])
    if "digest_contract" in prov:
        out.append("EVIDENCE GRADE: %s" % prov["digest_contract"])
    return out


def build():
    census = _load(CENSUS)
    fills = address_fills(census)
    filled = json.loads(json.dumps(census))
    by_key = {f["identity_key"]: f for f in fills}
    for hotel in filled["hotels"]:
        fill = by_key.get(hotel["identity_key"])
        if fill is None:
            continue
        if str(hotel.get("address") or "").strip():
            raise ApplicationError("%s already carries an address"
                                   % hotel["identity_key"])
        hotel["address"] = fill["address_filled"]
    if filled.get("count") != census.get("count"):
        raise ApplicationError("the census count moved")

    rows = {h["identity_key"]: h for h in filled["hotels"]}
    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"]}

    records, exclusions, applied = [], [], []
    for key, ruling in RULINGS.items():
        if key in published or key in excluded:
            raise ApplicationError("%s already holds authority" % key)
        row = rows[key]
        entries, prov = _evidence(key, ruling, row)
        caveats = _caveats(key, ruling, prov)
        if ruling["disposition"] == "VERIFIED_NO_PETS":
            for field in ("address", "city", "state", "postal_code"):
                if not str(row.get(field) or "").strip():
                    raise ApplicationError("%s: an exclusion needs %s" % (key, field))
            rec = OrderedDict((
                ("exclusion_id", "pgh-%s" % key.replace(" ", "-")),
                ("canonical_name", row["canonical_name"]),
                ("normalized_name", key),
                ("address", row["address"]), ("city", row["city"]),
                ("state", row["state"]), ("postal_code", row["postal_code"]),
                ("official_url", entries[0]["source_url"]),
                ("exclusion_state", HE.VERIFIED_NO_PETS),
                ("evidence_quote", entries[0]["quote"]),
                ("source_url", entries[0]["source_url"]),
                ("observed_at", entries[0]["captured_at"]),
                ("source_hash", entries[0]["artifact_sha256"]),
                ("reviewer_id", OPERATOR), ("reviewed_at", AS_OF),
                ("notes", " ".join(caveats)),
                ("market_id", MARKET_ID),
            ))
            rec["record_hash"] = HE.record_hash(rec)
            rec["approval_hash"] = HE.approval_hash(rec)
            exclusions.append(rec)
        else:
            facts = OrderedDict((
                ("pets_allowed", True),
                ("pet_fee", OrderedDict((("amount_cents", 7500),
                                         ("currency", "USD")))),
            ))
            rec = OrderedDict((
                ("key", key), ("name", row["canonical_name"]),
                ("facts", facts), ("evidence", entries),
                ("evidence_count", len(entries)),
                ("evidence_quote", entries[0]["quote"]),
                ("source_url", entries[0]["source_url"]),
                ("source_type", "EXACT_ENTITY_DOMAIN"),
                ("verification_state", "VERIFIED_PET_FRIENDLY"),
                ("verification_date", entries[0]["captured_at"]),
                ("verified_at", entries[0]["captured_at"]),
                ("worker_model_id", ""), ("worker_prompt_version", ""),
                ("worker_result_hash", entries[0]["artifact_sha256"].split(":")[-1]),
                ("worker_routing_version", ""), ("worker_validator_version", ""),
                ("schema_version", enums.POLICY_SCHEMA_VERSION),
                ("identity_key", key), ("market_id", MARKET_ID),
            ))
            rec["computation_class"] = classify(facts).computation_class
            # NO withheld_fields entry for fee_basis. The page never states
            # whether the $75 is per night or per stay, and genuine silence is
            # the ABSENCE of the field, not an entry claiming a decision was
            # made -- contracts.withholding refuses SOURCE_SILENT here
            # (SILENCE_IS_NOT_WITHHOLDING), and it agrees with this market's own
            # founder rule: "SOURCE SILENCE IS ABSENCE -- unstated optional
            # facts are absent, never withheld." So the amount publishes with no
            # basis and every consumer renders the basis as "Not stated".
            rec["approval"] = OrderedDict((
                ("decision", "APPROVED_AFTER_CURRENT_REVIEW"),
                ("operator", OPERATOR), ("approval_date", AS_OF),
                ("caveats", caveats),
                ("record_hash", PM.record_hash(
                    {k: v for k, v in rec.items() if k != "approval"})),
                ("evidence_hash", PM.evidence_hash(entries)),
            ))
            records.append(rec)
        applied.append(OrderedDict((
            ("identity_key", key), ("disposition", ruling["disposition"]),
            ("lane", ruling["lane"]),
            ("artifact_sha256", entries[0]["artifact_sha256"]),
            ("quote", entries[0]["quote"]))))

    package["hotels"] = list(package["hotels"]) + records
    problems = PM.validate_migrated(package)
    if problems:
        raise ApplicationError("the package does not validate: %s" % problems[:6])
    shard["exclusions"] = list(shard["exclusions"]) + exclusions
    shard["count"] = len(shard["exclusions"])
    HE.validate(shard)

    report = OrderedDict((
        ("schema", "ptf-market-founder-decisions/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("operator", OPERATOR),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("bright_data_authorised_but_unused", True),
        ("why_unused",
         "The one row this order could buy -- SpringHill Suites Pittsburgh "
         "Airport -- rendered in full on attended Chrome, so the $0.25 "
         "allowance was never drawn on."),
        ("records_added", len(records)),
        ("exclusions_added", len(exclusions)),
        ("census_addresses_filled", len(fills)),
        ("not_authorised_and_not_applied", [
            "courtyard by marriott pittsburgh west homestead waterfront "
            "(SAME_IDENTITY_SUPERSESSION proposed)",
            "comfort suites (canonical-name adoption proposed)",
            "intown suites extended stay pittsburgh pa (TRUE_CENSUS_ADD proposed)",
        ]),
        ("census_unchanged_at", filled["count"]),
        ("applied", applied),
        ("rulings", RULINGS),
    ))
    return filled, package, shard, fills, report


def run(write: bool) -> int:
    census, package, shard, fills, report = build()
    print("provider calls          : %d" % report["provider_calls"])
    print("spend                   : $%.2f" % report["usd_spent"])
    print("census                  : %d (unchanged)" % report["census_unchanged_at"])
    print("addresses filled        : %d" % len(fills))
    for f in fills:
        print("   %-52s %s" % (f["identity_key"][:51], f["address_filled"]))
    print("policy records added    : %d" % report["records_added"])
    print("exclusions added        : %d" % report["exclusions_added"])
    print("package after           : %d" % len(package["hotels"]))
    print("exclusion shard after   : %d" % shard["count"])
    print("NOT authorised, held    : %d" % len(report["not_authorised_and_not_applied"]))
    if not write:
        print("(check only -- pass --write)")
        return 0
    _write(CENSUS, census)
    print("WROTE %s" % CENSUS.name)
    _write(FILLS, OrderedDict((
        ("schema", "ptf-census-field-completion/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("what_this_is",
         "Street addresses filled on identities the census already held, each "
         "read from that identity's own first-party page. ADD-ONLY; row count "
         "and schema unchanged."),
        ("count", len(fills)), ("fills", fills))))
    print("WROTE %s" % FILLS.name)
    _write(PACKAGE, package)
    print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE exclusions shard (%d rows)" % shard["count"])
    _write(APPLICATION, report)
    print("WROTE %s" % APPLICATION.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except ApplicationError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
