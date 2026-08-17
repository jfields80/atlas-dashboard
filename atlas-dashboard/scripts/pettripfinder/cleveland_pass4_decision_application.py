"""PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 -- apply the founder's 23 rulings.

Deterministic application of the twenty-three founder decisions recorded
verbatim against ``cleveland_pass4_founder_review_packet.json`` (capture
commit b291400):

* TWO authorized identity renames land FIRST, atomically, in the committed
  census -- Days Inn Richfield -> Quality Inn & Suites Richfield and
  DoubleTree by Hilton Cleveland-Westlake -> Wyndham Garden Westlake. The
  census contract enforces ``identity_key == ptf_identity_key(canonical_name)``,
  so canonical_name, identity_key, slug and normalized_name move together.
  ``raw_name`` and ``display_name`` are left untouched: they already hold the
  prior brand strings and are the existing history mechanism, so no census
  schema field is added (the founder refused one for this work order).
* Sonesta ES Suites Cleveland Westlake is NOT renamed. The ES-Suites ->
  Simply-Suites observation stays CENSUS_HYGIENE_ONLY, consistent with the
  founder's earlier Cleveland Airport ruling; its policy publishes under the
  existing identity.
* 18 records publish (15 normal positives + 3 Batch-C publications). Every
  fact quote is re-asserted contiguous in its hash-bound artifact before
  anything is written; a failed assertion aborts the run.
* The two APPROVE_WITH_CHANGE rulings are structural, not cosmetic:
  - Crowne Plaza's weight is WITHHELD SOURCE_AMBIGUOUS because the page
    states "Pet weight limit: 30" with no unit, and the founder refused the
    pounds inference; its $75 pet damage deposit stays withheld too.
  - Embassy Suites' fee ladder is WITHHELD SOURCE_AMBIGUOUS because the
    source reads "$75 (14 nights)"; the founder refused repair-by-brand-
    pattern, so no tier boundary is selected.
* 5 refusals become VERIFIED_NO_PETS rows in the exclusion REGISTRY, each
  bound to its property-specific artifact by source_hash.
* Founder approvals are written ONLY against the FINAL record_hash /
  evidence_hash of each fully built record, and for the two renamed
  identities they bind the POST-rename record.
* Downstream: 18 seed rows, routing retired for all 23 decided identities,
  the renamed keys rewritten in routing and the unresolved manifest, the
  manifest reduced, the partition RE-DERIVED by its own builder, and the
  release contract re-pinned from derived authority.

The seven POLICY_NOT_FOUND rows gain no authority: silence is absence.

Run:  python -m scripts.pettripfinder.cleveland_pass4_decision_application \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder.contracts import census as census_contract        # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.contracts import withholding                      # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key    # noqa: E402
from scripts.pettripfinder.cleveland_pass4_capture_integration import (      # noqa: E402
    ROWS, load_json, quote_backed, verify_capture, write_lf,
)
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD           # noqa: E402
from scripts.pettripfinder.markets.contract import slugify as market_slugify  # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name   # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
ROUTING_PATH = LP / "identity_routing.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
MANIFEST_PATH = LP / "cleveland_unresolved_manifest.json"
PACKET_PATH = LP / "cleveland_pass4_founder_review_packet.json"
RESULTS_PATH = LP / "cleveland_pass4_capture_results.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))
RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-004/raw")

#: Founder decisions, verbatim scope, keyed by decision id.
DECISIONS: "OrderedDict[str, str]" = OrderedDict([
    ("P4P-01", "APPROVE"), ("P4P-02", "APPROVE"), ("P4P-03", "APPROVE"),
    ("P4P-04", "APPROVE_WITH_CHANGE"), ("P4P-05", "APPROVE_WITH_CHANGE"),
    ("P4P-06", "APPROVE"), ("P4P-07", "APPROVE"), ("P4P-08", "APPROVE"),
    ("P4P-09", "APPROVE"), ("P4P-10", "APPROVE"), ("P4P-11", "APPROVE"),
    ("P4P-12", "APPROVE"), ("P4P-13", "APPROVE"), ("P4P-14", "APPROVE"),
    ("P4P-15", "APPROVE"),
    ("P4R-01", "APPROVE_RENAME+APPROVE_PUBLICATION"),
    ("P4R-02", "APPROVE_RENAME+APPROVE_PUBLICATION"),
    ("P4R-03", "CENSUS_HYGIENE_ONLY+APPROVE_PUBLICATION"),
    ("P4N-01", "APPROVE_VERIFIED_NO_PETS"),
    ("P4N-02", "APPROVE_VERIFIED_NO_PETS"),
    ("P4N-03", "APPROVE_VERIFIED_NO_PETS"),
    ("P4N-04", "APPROVE_VERIFIED_NO_PETS"),
    ("P4N-05", "APPROVE_VERIFIED_NO_PETS"),
])

#: The two authorized renames: old identity_key -> new canonical name.
RENAMES: "OrderedDict[str, str]" = OrderedDict([
    ("days inn richfield", "Quality Inn & Suites Richfield"),
    ("doubletree by hilton cleveland westlake", "Wyndham Garden Westlake"),
])

#: The ruling text preserved into each record's approval caveats.
RULING_NOTES: Dict[str, str] = {
    "P4P-01": "Founder P4P-01: approve the source-supported facts exactly as "
              "presented; SOURCE SILENCE = ABSENCE.",
    "P4P-02": "Founder P4P-02: approve as presented, including the canonical "
              "top-level fee_cap ($75 per stay, qualifier_stated true) and "
              "the per_room nightly fee with scope_pet_allowance 2. The "
              "identity check at 4222 W 150th / 44135 / 216-251-8500 is "
              "accepted; the Pass-3 Airport West redirect did not recur.",
    "P4P-03": "Founder P4P-03: approve as presented; do not invent fee scope "
              "beyond what the page states.",
    "P4P-04": "Founder P4P-04 (APPROVE_WITH_CHANGE): publish pets_allowed, "
              "the $75 per-night fee, the two-pet limit and dogs+cats. The "
              "weight is NOT published: the page states 'Pet weight limit: "
              "30' with no unit, and pounds may not be inferred from corpus "
              "convention or brand context, so weight_limit is withheld "
              "SOURCE_AMBIGUOUS with the exact quote. The $75 pet damage "
              "deposit stays withheld SOURCE_AMBIGUOUS -- refundability is "
              "unstated and is never inferred.",
    "P4P-05": "Founder P4P-05 (APPROVE_WITH_CHANGE): publish pets_allowed, "
              "the two-pet limit and dogs+cats. The fee ladder is NOT "
              "published: the source reads '$75 (14 nights), $125 (5+ "
              "nights)', and founder policy requires source-supported "
              "canonicalization rather than repair-by-brand-pattern, so "
              "fee_tiers is withheld SOURCE_AMBIGUOUS with the malformed "
              "wording preserved verbatim and no tier boundary selected.",
    "P4P-06": "Founder P4P-06: publish the non-monetary facts; the cleaning "
              "fee stays withheld SCHEMA_CANNOT_REPRESENT because both "
              "monetary rungs are ceilings. CEILING != PRICE -- $25 and $15 "
              "are never published as exact charges.",
    "P4P-07": "Founder P4P-07: approve as presented; the adjacent $75 "
              "per-stay line is the first tier of the same source-stated "
              "ladder, not a second independent charge.",
    "P4P-08": "Founder P4P-08: approve as presented -- night one at $25 per "
              "night per pet, nights two onward at $5 per night with NO "
              "invented second-rung scope. The 2715/2716 Creekside "
              "discrepancy is not part of this policy approval and is "
              "recorded as census hygiene.",
    "P4P-09": "Founder P4P-09: approve as presented. The $105 cap belongs to "
              "the SECOND PET (trigger_max_nights 7) and is never modelled "
              "as a room or property cap; service-animal prose is never "
              "moved into general_restrictions.",
    "P4P-10": "Founder P4P-10: approve on THIS property's own captured page "
              "and identity binding, not on brand inheritance, with the same "
              "second-pet schedule and cap treatment.",
    "P4P-11": "Founder P4P-11: approve the shared facts plus this property's "
              "own unattended-pet and leash restrictions, which publish "
              "because THIS page states them and are never inferred for "
              "sibling Red Roof properties.",
    "P4P-12": "Founder P4P-12: approve as presented. The $100 refundable "
              "deposit is property-wide wording applying to all guests, NOT "
              "a pet deposit; it stays withheld SOURCE_AMBIGUOUS with the "
              "exact sentence retained.",
    "P4P-13": "Founder P4P-13: approve as presented -- the page supplies "
              "both fee basis and scope, so no inference is needed.",
    "P4P-14": "Founder P4P-14: approve as presented. Fee scope remains "
              "ABSENT because the page states neither per-room nor per-pet; "
              "no species, weight, restriction or deposit structure is "
              "invented and no withholding is required. The census "
              "canonical-name observation is hygiene only.",
    "P4P-15": "Founder P4P-15: approve as presented. Unlike the malformed "
              "Embassy Suites source, this page states '$75(1-4n) $125(5+)' "
              "explicitly, so no repair or normalization of the band is "
              "involved.",
    "P4R-01": "Founder P4R-01: identity rename AUTHORIZED (Days Inn "
              "Richfield -> Quality Inn & Suites Richfield) and publication "
              "approved under the resulting identity. The changed phone is "
              "part of the brand conversion, not evidence of a different "
              "lodging identity; street, ZIP and the Choice property code "
              "oh330 bind. Fee scope is not invented.",
    "P4R-02": "Founder P4R-02: identity rename AUTHORIZED (DoubleTree by "
              "Hilton Cleveland-Westlake -> Wyndham Garden Westlake) on same "
              "street, ZIP and phone plus a genuine 404 on the old Hilton "
              "page, and publication approved. The $150 sanitation charge is "
              "discretionary and stays withheld SOURCE_AMBIGUOUS -- never "
              "general_restrictions.",
    "P4R-03": "Founder P4R-03: identity rename NOT authorized. The ES Suites "
              "-> Simply Suites observation is CENSUS_HYGIENE_ONLY, "
              "consistent with the Cleveland Airport sibling's earlier "
              "ruling, so the policy publishes under the existing identity. "
              "Dogs only -- cats are never claimed; the $50 deposit stays "
              "withheld SCHEMA_CANNOT_REPRESENT because refundability is "
              "unstated.",
}

NEGATIVE_NOTES: Dict[str, str] = {
    "P4N-01": "Founder P4N-01: explicit first-party refusal; no pet-friendly "
              "authority may be created, and service-animal silence on this "
              "surface does not change the refusal.",
    "P4N-02": "Founder P4N-02: the refusal explicitly names the Cottages and "
              "therefore binds this identity; the service-animal exception "
              "is legal-access wording, not guest-pet permission.",
    "P4N-03": "Founder P4N-03: explicit first-party refusal. The $500 charge "
              "for bringing a non-service animal into a guest room is a "
              "penalty for violating the no-pets policy and is NEVER modelled "
              "as a pet fee.",
    "P4N-04": "Founder P4N-04: the service-animal clause and the pet refusal "
              "are correctly separated; service-animal access is never "
              "pet-friendly lodging.",
    "P4N-05": "Founder P4N-05: explicit first-party refusal. The observed "
              "'Quality Inn Akron South' versus census 'Quality Inn "
              "Arlington' is census/display-name hygiene only -- no rename "
              "in this work order.",
}

#: Census-hygiene observations the founder explicitly separated from policy.
HYGIENE: List[Dict] = [
    OrderedDict([("identity_key", "comfort suites twinsburg"),
                 ("field", "address"),
                 ("census", "2715 Creekside Dr"),
                 ("observed", "2716 Creekside Drive"),
                 ("decision_ref", "P4P-08"),
                 ("ruling", "not part of the policy approval; do not alter "
                            "the census address without an authoritative "
                            "identity source")]),
    OrderedDict([("identity_key", "towneplace suites by marriott"),
                 ("field", "canonical_name"),
                 ("census", "TownePlace Suites by Marriott"),
                 ("observed", "TownePlace Suites Cleveland Solon"),
                 ("decision_ref", "P4P-14"),
                 ("ruling", "display-name hygiene only")]),
    OrderedDict([("identity_key", "quality inn arlington"),
                 ("field", "canonical_name"),
                 ("census", "Quality Inn Arlington"),
                 ("observed", "Quality Inn Akron South"),
                 ("decision_ref", "P4N-05"),
                 ("ruling", "display-name hygiene only; no rename here")]),
    OrderedDict([("identity_key", "sonesta es suites cleveland westlake"),
                 ("field", "canonical_name"),
                 ("census", "Sonesta ES Suites Cleveland Westlake"),
                 ("observed", "Sonesta Simply Suites Cleveland Westlake"),
                 ("decision_ref", "P4R-03"),
                 ("ruling", "CENSUS_HYGIENE_ONLY -- identity_key unchanged; "
                            "if this rebrand is ever canonicalized, both "
                            "Cleveland Sonesta properties move in one "
                            "dedicated census-normalization ruling")]),
    OrderedDict([("identity_key", "quality inn and suites richfield"),
                 ("field", "phone"),
                 ("census", "330.659.6151"),
                 ("observed", "(330) 523-5329"),
                 ("decision_ref", "P4R-01"),
                 ("ruling", "the phone changed with the flag conversion; "
                            "recorded as hygiene, not applied")]),
]


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _clean_url(url: str) -> str:
    return (url or "").split("?", 1)[0]


def _value_display(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------- #
# The two APPROVE_WITH_CHANGE rulings, applied to the adjudication specs.
# --------------------------------------------------------------------------- #

def founder_adjusted(qid: str, spec: Dict) -> Tuple[List[Dict], List[Dict]]:
    facts = copy.deepcopy(list(spec.get("facts", [])))
    withheld = copy.deepcopy(list(spec.get("withheld", [])))

    if qid == "CLE-RR-008":                      # P4P-04 Crowne Plaza
        weight = [f for f in facts if f["field"] == "weight_limit"]
        facts = [f for f in facts if f["field"] != "weight_limit"]
        withheld.append(OrderedDict([
            ("field", "weight_limit"),
            ("reason_code", enums.SOURCE_AMBIGUOUS),
            ("reason", "The page states 'Pet weight limit: 30' with no unit. "
                       "Pounds may not be inferred from corpus convention or "
                       "brand context, so no weight publishes and the exact "
                       "wording is retained (founder P4P-04)."),
            ("quote", weight[0]["quote"]),
        ]))
    if qid == "CLE-RR-011":                      # P4P-05 Embassy Suites
        tiers = [f for f in facts if f["field"] == "fee_tiers"]
        facts = [f for f in facts if f["field"] != "fee_tiers"]
        withheld.append(OrderedDict([
            ("field", "fee_tiers"),
            ("reason_code", enums.SOURCE_AMBIGUOUS),
            ("reason", "The source reads '$75 (14 nights), $125 (5+ "
                       "nights)'. The first band is malformed, and founder "
                       "policy requires source-supported canonicalization "
                       "rather than repair-by-brand-pattern, so no tier "
                       "boundary is selected and no schedule publishes until "
                       "the source is unambiguous (founder P4P-05)."),
            ("quote", tiers[0]["quote"]),
        ]))
    return facts, withheld


# --------------------------------------------------------------------------- #
# Evidence-quote regions: one verbatim slice of the page, never stitched.
# --------------------------------------------------------------------------- #

def build_evidence_quote(qid: str, doc: Dict, quotes: List[str]) -> str:
    """The smallest contiguous window of the captured page covering every quote.

    A window is a real slice of what the property published. Where the quotes
    are too far apart for one window to be honest prose, the regions are joined
    with a bracketed ellipsis so nobody can read the join as contiguity.
    """
    seen: List[str] = []
    for quote in quotes:
        if quote not in seen:
            seen.append(quote)
    for source in ("text", "html"):
        body = doc.get(source, "")
        if source == "html":
            body = re.sub(r"<[^>]+>", " ", body)
        hay = _c(body)
        spots = []
        ok = True
        for quote in seen:
            i = hay.find(_c(quote))
            if i < 0:
                ok = False
                break
            spots.append((i, i + len(_c(quote))))
        if not ok:
            continue
        start, end = min(s for s, _ in spots), max(e for _, e in spots)
        if end - start <= 3000:
            return hay[start:end]
        return " […] ".join(hay[s:e] for s, e in sorted(spots))
    raise AssertionError("%s: no source carries every quote" % qid)


# --------------------------------------------------------------------------- #
# Record construction.
# --------------------------------------------------------------------------- #

def _evidence_entry(field: str, quote: str, source_url: str, value_disp: str,
                    artifact_sha: str, captured_at: str,
                    method: str) -> Dict:
    entry = OrderedDict([
        ("field", field),
        ("quote", quote),
        ("source_url", source_url),
        ("value", value_disp),
        ("evidence_ref", ""),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", artifact_sha),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", captured_at),
        ("capture_method", method),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
    ])
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def build_positive_record(decision_id: str, qid: str, spec: Dict,
                          census_row: Dict, doc: Dict) -> Dict:
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % qid)
    artifact_sha = "sha256:%s" % integrity["html_sha256"]
    source_url = _clean_url(doc["final_url"])
    method = spec.get("capture_method",
                      doc.get("capture_method", "attended_browser"))

    facts_list, withheld_list = founder_adjusted(qid, spec)

    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    evidence: List[Dict] = []
    all_quotes: List[str] = []
    for fact in facts_list:
        if quote_backed(fact["quote"], doc) == "MISSING":
            raise AssertionError("%s: quote %r not in artifact"
                                 % (qid, fact["quote"][:60]))
        evidence.append(_evidence_entry(
            fact["field"], fact["quote"], source_url,
            _value_display(fact["value"]), artifact_sha, doc["captured_at"],
            method))
        all_quotes.append(fact["quote"])
        if fact["field"] == "service_animal_statement":
            sas = fact["value"]
        else:
            facts[fact["field"]] = fact["value"]

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in withheld_list:
        quotes = [w["quote"]] + list(
            spec.get("extra_withheld_quotes", {}).get(w["field"], []))
        refs = []
        for quote in quotes:
            if quote_backed(quote, doc) == "MISSING":
                raise AssertionError("%s: withheld quote %r not in artifact"
                                     % (qid, quote[:60]))
            entry = _evidence_entry(w["field"], quote, source_url, "WITHHELD",
                                    artifact_sha, doc["captured_at"], method)
            evidence.append(entry)
            all_quotes.append(quote)
            refs.append(entry["evidence_ref"])
        if w["field"] in facts:
            raise AssertionError("%s: %s is both published and withheld"
                                 % (qid, w["field"]))
        withheld[w["field"]] = OrderedDict([
            ("reason_code", w["reason_code"]),
            ("reason", w["reason"]),
            ("evidence_refs", refs),
        ])

    evidence_quote = build_evidence_quote(qid, doc, all_quotes)
    for entry in evidence:
        if _c(entry["quote"]) not in _c(evidence_quote):
            raise AssertionError("%s: quote %r escapes evidence_quote"
                                 % (qid, entry["quote"][:60]))

    record = OrderedDict([
        ("key", census_row["identity_key"]),
        ("name", census_row["canonical_name"]),
        ("facts", facts),
        ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", evidence_quote),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE),
        ("verified_at", DECISION_DATE),
        ("worker_model_id", ""),
        ("worker_prompt_version", ""),
        ("worker_result_hash", artifact_sha),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]),
        ("market_id", MARKET),
    ])
    if withheld:
        record["withheld_fields"] = withheld
    if sas is not None:
        record["service_animal_statement"] = sas
    record["computation_class"] = classify(facts).computation_class

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record)) \
        + list(withholding.validate(record))
    if issues:
        raise AssertionError("%s: contract issues: %s" % (qid, issues[:4]))

    caveats = [
        "Founder decision %s, %s, approved against THIS record_hash. Facts "
        "were constructed only from quotes verified contiguous in the "
        "hash-bound attended capture (%s); identity was bound on the page's "
        "own address/ZIP/phone signals recorded in "
        "cleveland_pass4_capture_results.json." % (
            decision_id, WORK_ORDER, artifact_sha[:23]),
    ]
    note = RULING_NOTES.get(decision_id)
    if note:
        caveats.append(note)
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(decision_id: str, neg: Dict, census_row: Dict,
                    doc: Dict) -> Dict:
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % neg["queue_id"])
    if quote_backed(neg["refusal_quote"], doc) == "MISSING":
        raise AssertionError("%s: refusal quote not in artifact"
                             % neg["queue_id"])
    source_url = _clean_url(doc["final_url"])
    record = OrderedDict([
        ("exclusion_id", "cle-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", neg["refusal_quote"]),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE),
        ("source_hash", "sha256:%s" % integrity["html_sha256"]),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "%s, %s: affirmative refusal in the property's own words, "
                  "captured with retained bytes by the attended browser (%s). "
                  "%s Service-animal access is a legal category and is never "
                  "read as a pet permission or as a refusal on its own."
                  % (decision_id, WORK_ORDER, neg["queue_id"],
                     NEGATIVE_NOTES[decision_id])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# --------------------------------------------------------------------------- #
# Renames.
# --------------------------------------------------------------------------- #

def apply_renames(census_doc: Dict) -> List[Dict]:
    """The two authorized renames, atomically, with history left intact."""
    rows = {r["identity_key"]: r for r in census_doc["hotels"]}
    applied = []
    for old_key, new_name in RENAMES.items():
        if old_key not in rows:
            raise SystemExit("STOP: %r is not in the census" % old_key)
        row = rows[old_key]
        new_key = ptf_identity_key(new_name)
        if new_key in rows:
            raise SystemExit("STOP: %r already exists" % new_key)
        before = OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]),
            ("normalized_name", row["normalized_name"]),
        ])
        row["canonical_name"] = new_name
        row["identity_key"] = new_key
        row["normalized_name"] = normalize_name(new_name)
        # The corpus slug comes from the canonical NAME, not the key: the key
        # spells "&" as "and" while the slug drops it entirely
        # (cambria-hotel-suites-avon). Deriving it from the key would mint a
        # slug no other row uses and disagree with the route the renderer
        # builds for this hotel.
        row["slug"] = market_slugify(new_name)
        applied.append(OrderedDict([
            ("decision_ref", "P4R-01" if old_key == "days inn richfield"
             else "P4R-02"),
            ("before", before),
            ("after", OrderedDict([
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("slug", row["slug"]),
                ("normalized_name", row["normalized_name"]),
            ])),
            ("history_preserved", OrderedDict([
                ("raw_name", row.get("raw_name")),
                ("display_name", row.get("display_name")),
                ("mechanism", "existing census fields; no schema field added"),
            ])),
        ]))
    issues = list(census_contract.validate(census_doc))
    if issues:
        raise AssertionError("census contract issues after rename: %s"
                             % issues[:4])
    return applied


def rewrite_keys(doc, mapping: Dict[str, str]) -> int:
    """Rewrite renamed identity keys/slugs/names anywhere they appear."""
    blob = json.dumps(doc, ensure_ascii=False)
    hits = 0
    for old_key, (new_key, old_name, new_name, old_slug, new_slug) in \
            mapping.items():
        for a, b in ((old_key, new_key), (old_name, new_name),
                     (old_slug, new_slug)):
            hits += blob.count(a)
            blob = blob.replace(a, b)
    return json.loads(blob), hits


# --------------------------------------------------------------------------- #
# Application.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    packet = load_json(PACKET_PATH)
    ledger = load_json(RESULTS_PATH)

    positives = {c["decision_id"]: c for c in packet["positive_candidates"]}
    renames_p = {c["decision_id"]: c for c in packet["rename_candidates"]}
    negatives = {c["decision_id"]: c for c in packet["negative_candidates"]}
    if set(DECISIONS) != set(positives) | set(renames_p) | set(negatives):
        raise SystemExit("STOP: decisions do not cover the packet exactly")
    if len(DECISIONS) != 23:
        raise SystemExit("STOP: expected 23 decisions")

    facts_doc = load_json(FACTS_PATH)
    census_doc = load_json(CENSUS_PATH)
    exclusions_doc = load_json(EXCLUSIONS_PATH)
    before = OrderedDict([
        ("census", census_doc["count"]),
        ("published", len(facts_doc["hotels"])),
        ("verified_no_pets", len([
            e for e in exclusions_doc["exclusions"]
            if e.get("market_id") == MARKET
            and e["exclusion_state"] == EX.VERIFIED_NO_PETS])),
    ])
    if (before["published"], before["verified_no_pets"]) != (81, 35):
        raise SystemExit("STOP: Cleveland baseline is not 81/35: %s" % before)

    # ---- 1. renames first --------------------------------------------------- #
    rename_log = apply_renames(census_doc)
    census_rows = {r["identity_key"]: r for r in census_doc["hotels"]}
    key_map = {}
    for entry in rename_log:
        b, a = entry["before"], entry["after"]
        key_map[b["identity_key"]] = (a["identity_key"], b["canonical_name"],
                                      a["canonical_name"], b["slug"],
                                      a["slug"])
    renamed_key = {b: v[0] for b, v in key_map.items()}

    # ---- 2. publications ---------------------------------------------------- #
    published: List[Dict] = []
    have = {h["identity_key"] for h in facts_doc["hotels"]}
    for decision_id in DECISIONS:
        if decision_id.startswith("P4N"):
            continue
        cand = positives.get(decision_id) or renames_p[decision_id]
        qid = cand["queue_id"]
        spec = ROWS[qid]
        key = renamed_key.get(cand["identity_key"], cand["identity_key"])
        if key not in census_rows:
            raise SystemExit("STOP %s: %r not in the census" % (qid, key))
        if key in have:
            raise SystemExit("STOP %s: %r already published" % (qid, key))
        artifact = spec.get("quote_artifact") or spec["artifact"]
        doc = load_json(raw_dir / artifact)
        published.append(build_positive_record(decision_id, qid, spec,
                                               census_rows[key], doc))
    if len(published) != 18:
        raise SystemExit("STOP: expected 18 publications, built %d"
                         % len(published))
    facts_doc["hotels"] = facts_doc["hotels"] + published

    # ---- 3. exclusions ------------------------------------------------------ #
    existing_norm = {e["normalized_name"] for e in exclusions_doc["exclusions"]}
    new_exclusions: List[Dict] = []
    for decision_id in ("P4N-01", "P4N-02", "P4N-03", "P4N-04", "P4N-05"):
        neg = negatives[decision_id]
        key = neg["identity_key"]
        if key not in census_rows:
            raise SystemExit("STOP %s: %r not in the census"
                             % (neg["queue_id"], key))
        spec = ROWS[neg["queue_id"]]
        artifact = spec.get("quote_artifact") or spec["artifact"]
        doc = load_json(raw_dir / artifact)
        record = build_exclusion(decision_id, neg, census_rows[key], doc)
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % neg["queue_id"])
        new_exclusions.append(record)
    exclusions_doc["exclusions"] = (exclusions_doc["exclusions"]
                                    + new_exclusions)
    EX.validate(exclusions_doc)

    # ---- 4. seed rows ------------------------------------------------------- #
    seed_new = []
    for record in published:
        row = census_rows[record["identity_key"]]
        seed_new.append({
            "name": record["name"], "category": "pet-friendly-hotels",
            "address": row["address"], "city": row["city"],
            "state": row["state"], "postal_code": row["postal_code"],
            "phone": row["phone"], "website_url": record["source_url"],
            "source_url": record["source_url"],
            "source_type": "OFFICIAL_PROPERTY", "observed_at": DECISION_DATE,
            "rating": "", "amenities": "",
            "pet_policy": record["evidence_quote"], "canonical": "",
            MARKET_ID_FIELD: MARKET,
        })

    # ---- 5. routing + manifest ---------------------------------------------- #
    routing = load_json(ROUTING_PATH)
    routing, routing_hits = rewrite_keys(routing, key_map)
    decided_norm = {normalize_name(r["name"]) for r in published} | \
                   {e["normalized_name"] for e in new_exclusions}
    before_routes = len(routing["routes"])
    routing["routes"] = [r for r in routing["routes"]
                         if not (r.get("market_id") == MARKET
                                 and r["hotel_ref"]["normalized_name"]
                                 in decided_norm)]
    routing["count"] = len(routing["routes"])
    routes_retired = before_routes - len(routing["routes"])

    manifest = load_json(MANIFEST_PATH)
    manifest, manifest_hits = rewrite_keys(manifest, key_map)
    resolved_keys = {r["identity_key"] for r in published} | \
                    {e["normalized_name"] for e in new_exclusions}
    keep = [i for i in manifest["items"]
            if i["normalized_name"] not in resolved_keys
            and i.get("identity_key") not in resolved_keys]
    removed = len(manifest["items"]) - len(keep)
    if removed != 23:
        raise SystemExit("STOP: expected 23 manifest removals, got %d"
                         % removed)
    manifest["items"] = keep
    manifest["as_of"] = DECISION_DATE
    manifest["pass4_update"] = (
        "%s removed 23 rows (18 published, 5 verified no-pets) and rewrote "
        "two renamed identity keys; every removal is traceable in "
        "cleveland_pass4_capture_results.json." % WORK_ORDER)

    summary = OrderedDict([
        ("before", before),
        ("renames_applied", rename_log),
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("seed_rows_added", len(seed_new)),
        ("routes_retired", routes_retired),
        ("renamed_key_rewrites",
         {"identity_routing": routing_hits,
          "unresolved_manifest": manifest_hits}),
        ("manifest_removed", removed),
    ])

    if apply:
        write_lf(CENSUS_PATH, census_doc)
        payload = write_lf(FACTS_PATH, facts_doc)
        new_sha = hashlib.sha256(payload).hexdigest()
        write_lf(EXCLUSIONS_PATH, exclusions_doc)
        write_lf(ROUTING_PATH, routing)

        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            existing_rows = list(reader)
            fields = list(reader.fieldnames)
        existing_names = {normalize_name(r["name"]) for r in existing_rows
                          if r.get(MARKET_ID_FIELD) == MARKET}
        clash = existing_names & {normalize_name(r["name"])
                                  for r in seed_new}
        if clash:
            raise SystemExit("STOP: seed rows already present: %s" % clash)
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in existing_rows + seed_new:
            writer.writerow({k: row.get(k, "") for k in fields})
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8",
                                  newline="")

        MANIFEST_PATH.write_bytes(
            (json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
            .encode("utf-8"))

        from scripts.pettripfinder.cleveland_final_partition_002 import (
            _write_json as _write_partition, build_partition)
        partition = build_partition()
        # The manifest states this market's reconciliation of record, and the
        # assembler's authority gate compares it against the contract. Its
        # summary is DERIVED from the rebuilt partition, never hand-set, then
        # the partition is rebuilt once more so both agree byte for byte.
        rec = partition["reconciliation"]
        manifest["published_pet_friendly"] = rec["published_pet_friendly"]
        manifest["verified_no_pets"] = rec["verified_no_pets"]
        manifest["resolved"] = rec["resolved"]
        manifest["unresolved"] = rec["unresolved"]
        manifest["classification_counts"] = OrderedDict(
            sorted(Counter(i["classification"]
                           for i in manifest["items"]).items()))
        MANIFEST_PATH.write_bytes(
            (json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        partition = build_partition()
        _write_partition(PARTITION_PATH, partition)
        counts = Counter(i["final_state"] for i in partition["items"])

        from scripts.pettripfinder.build_market_manifest import build_package
        pkg = build_package(MARKET)
        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        contract["policy_package"]["expected_record_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["reconciliation"].update(
            {k: v for k, v in partition["reconciliation"].items()
             if k in contract["reconciliation"]})
        contract["public_surface"]["seed_hotel_rows"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["public_surface"]["public_hotel_profile_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["routes"]["hotel_route_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["routes"]["published_corridor_route_count"] = \
            len(pkg.corridor_routes)
        contract["deployment_authorization"]["means"] = re.sub(
            r"\d+ of this market's 188",
            "%d of this market's 188" % partition["reconciliation"]["unresolved"],
            contract["deployment_authorization"]["means"])
        write_lf(CONTRACT_PATH, contract)

        packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
        packet["decided_at"] = DECISION_DATE
        packet["decided_by"] = FOUNDER
        packet["decision_work_order"] = WORK_ORDER
        for group, store in (("positive_candidates", positives),
                             ("rename_candidates", renames_p),
                             ("negative_candidates", negatives)):
            for cand in packet[group]:
                cand["founder_decision"] = DECISIONS[cand["decision_id"]]
                cand["outcome"] = (
                    "EXCLUDED_VERIFIED_NO_PETS"
                    if group == "negative_candidates" else "PUBLISHED")
        packet["identity_renames_applied"] = rename_log
        packet["census_hygiene_recorded_not_applied"] = HYGIENE
        packet["policy_not_found_unresolved"] = sorted(
            r["queue_id"] for r in ledger["results"]
            if r["outcome"] == "POLICY_NOT_FOUND")
        write_lf(PACKET_PATH, packet)

        report_path = LP / "cleveland_artifact_verification_001.json"
        report = load_json(report_path)
        report["facts_sha256_after_pass4_decisions"] = new_sha
        write_lf(report_path, report)

        summary["facts_sha256"] = new_sha
        summary["after"] = OrderedDict([
            ("census", partition["reconciliation"]["confirmed_identities"]),
            ("published", counts["PUBLISHED_PET_FRIENDLY"]),
            ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
            ("unresolved", partition["reconciliation"]["unresolved"]),
        ])
        summary["final_state_counts"] = OrderedDict(sorted(counts.items()))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=Path("C:/Atlas/atlas-dashboard/data"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.data_root, args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value, ensure_ascii=False)
                          if not isinstance(value, str) else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
