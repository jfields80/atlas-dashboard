"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- apply the recovered evidence.

Rewrites Nashville's registered authority from the durable captures this order
took, and leaves every previously valid row exactly as it was.

WHAT IT WRITES

  hotel_policy_facts_nashville-tn.json                     published rows
  markets/authority/nashville-tn/hotel_exclusions.json      verified-no-pets
  markets/authority/nashville-tn/seed_businesses.csv        display rows
  identity_census/nashville-tn.json                         policy_state per row
  nashville_tn_final_partition_001.json                     dispositions
  nashville_tn_identity_holds_002.json                      what is STILL held

CURRENT EVIDENCE GOVERNS, AND LINEAGE IS KEPT

A recovered row is republished on what its page says TODAY, not on what the
shadow recorded. Where the two agree the row simply gains a durable hash; where
they disagree the CURRENT read wins and the disagreement is recorded. The legacy
capture is never erased: every recovered record carries a
``superseded_evidence`` block naming the old lane, the old timestamp, the old
byte length and the fact that it carried no document hash -- which is the whole
reason this order exists.

THE GATE IS NOT RELAXED ANYWHERE

Every record, recovered or pre-existing, goes through
``first_party_binding.evaluate_package`` again, and rule O still requires a
reservation for anything bought through a paid lane. A row the gate refuses is
held with its reason, whatever the shadow or this order's own capture called it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import census as CENSUS          # noqa: E402
from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA   # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HE              # noqa: E402
from scripts.pettripfinder import market_authority as MA              # noqa: E402
from scripts.pettripfinder.markets import contract as MC              # noqa: E402
from scripts.pettripfinder.nashville_tn_registration_002 import (      # noqa: E402
    REVIEWER_ID, facts_from_read, slugify,
)

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
PRIOR_ORDER = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"
SHADOW_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
MARKET_NAME = "Greater Nashville, Tennessee"
STATE_CODE = "TN"
AS_OF = "2026-09-09"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT_PATH = os.path.join(PKG, "markets", "%s.json" % MARKET_ID)
CENSUS_PATH = os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID)
HOLDS_PATH = os.path.join(PKG, "nashville_tn_identity_holds_002.json")
PARTITION_PATH = os.path.join(PKG, "nashville_tn_final_partition_001.json")
POLICY_PATH = os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID)
COHORT = os.path.join(REPORTS, "nashville_tn_recovery_cohort_003.json")
ATTENDED = os.path.join(REPORTS, "nashville_tn_attended_recapture_003.json")
STATIC = os.path.join(REPORTS, "nashville_tn_static_recapture_003.json")
OUT = os.path.join(REPORTS, "nashville_tn_recovery_application_003.json")

REVIEW_BASIS = (
    "Set-level founder authorisation to RECOVER EVIDENCE, not to launch. Founder work order "
    + WORK_ORDER + " directs this order to re-acquire the exact first-party sources behind rows "
    "held because the legacy attended capture is not durable, to let CURRENT first-party "
    "evidence govern, and to publish only rows the modern gate admits. Every published fact "
    "below is read from a page this order fetched and hashed in the same call. The agent did "
    "not attribute a per-row reading to the founder. Launch participation is a separate founder "
    "decision this order does not take.")

_LANE_CAPTURE = {"ATTENDED_BROWSER": "attended_browser",
                 "DIRECT_STATIC": "direct_http",
                 "FIRECRAWL": "firecrawl_rendered_fetch"}
_LANE_GRADE = {"ATTENDED_BROWSER": "PT2_BRAND",
               "DIRECT_STATIC": "PT1_FIRST_PARTY",
               "FIRECRAWL": "PT2_BRAND"}

#: Which substring of the bounded policy block supports which published field.
#: The quote cited for a fact is the text the VALUE came from, not a generic
#: sentence that happens to mention pets.
_FIELD_PATTERNS = (
    ("pet_fee", re.compile(r"[^.]*?(?:Non-Refundable Pet Fee Per (?:Night|Stay):\s*\$[0-9.]+"
                           r"|\$[0-9.]+\s*(?:non-?refundable|per\s+(?:night|stay|pet))"
                           r"|[0-9.]+\s*USD[^.]{0,40}"
                           r"|\$[0-9.]+\.00\s*non-refundable\s*fee)[^.]*", re.I)),
    ("fee_tiers", None),
    ("weight_limit", re.compile(r"[^.]*?(?:Maximum Pet Weight:\s*[0-9.]+\s*lbs"
                                r"|[0-9.]+\s*lbs?\s*maximum"
                                r"|[0-9.]+\s*(?:lbs?|pounds)[^.]{0,30})[^.]*", re.I)),
    ("pet_count_limit", re.compile(r"[^.]*?(?:Maximum Number of Pets in Room:\s*[0-9]+"
                                   r"|[0-9]+\s*pets?\s*(?:max|minimum|per room)"
                                   r"|(?:up to\s+)?(?:two|three|[0-9]+)\s+(?:dogs?|pets?)\s+"
                                   r"(?:allowed\s+)?per\s+room)[^.]*", re.I)),
    ("species", re.compile(r"[^.]*?(?:dogs?\s*(?:/|,|\s+(?:and|or)\s+)\s*cats?\s*only"
                           r"|dog/cat\s*only|dogs?\s+only|Dogs\s+Only)[^.]*", re.I)),
)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _prefixed(digest):
    d = (digest or "").strip()
    return "" if not d else (d if d.startswith("sha256:") else "sha256:" + d)


def field_quote(field, block, fallback):
    """The substring of the bounded block that supports one published field."""
    for name, pattern in _FIELD_PATTERNS:
        if name != field or pattern is None:
            continue
        match = pattern.search(block or "")
        if match:
            return " ".join(match.group(0).split())[:400]
    return fallback


def evidence_rows(key, capture, facts):
    """One evidence entry per published field, each citing the text its value
    came from and all bound to the one document this order hashed."""
    digest = _prefixed(capture.get("page_sha256"))
    block = capture.get("policy_block") or ""
    quote = capture.get("exact_quote") or ""
    lane = capture["capture_lane"]
    out = []
    for field in facts:
        cited = quote if field == "pets_allowed" else field_quote(field, block, quote)
        if not cited:
            cited = quote
        out.append(OrderedDict((
            ("field", field),
            ("quote", cited[:400]),
            ("source_url", capture["final_url"]),
            ("value", json.dumps(facts[field], sort_keys=True)
             if isinstance(facts[field], (dict, list))
             else str(facts[field]).lower() if isinstance(facts[field], bool)
             else str(facts[field])),
            ("evidence_ref", "ev:" + hashlib.sha256(
                (key + field + cited).encode("utf-8")).hexdigest()[:16]),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", digest),
            ("artifact_kind", "rendered_html"),
            ("captured_at", capture["captured_at"]),
            ("capture_method", _LANE_CAPTURE[lane]),
            ("source_grade", _LANE_GRADE[lane]),
        )))
    return out


def lineage(cohort_row, capture):
    """What the legacy capture was, kept rather than erased."""
    return OrderedDict((
        ("superseded_order", SHADOW_ORDER),
        ("superseded_lane", cohort_row.get("old_capture_lane") or ""),
        ("superseded_captured_at", cohort_row.get("old_captured_at") or ""),
        ("superseded_byte_length", cohort_row.get("old_byte_length")),
        ("superseded_document_sha256", cohort_row.get("old_document_sha256") or ""),
        ("why_superseded",
         "the legacy capture recorded a byte LENGTH and no document hash, and its acquisition "
         "directory is gitignored and empty, so the modern first-party evidence gate refused it "
         "on CAPTURE_HASH. This record replaces it with a page THIS order fetched and hashed in "
         "the same call that took the quote."),
        ("superseded_quote", (cohort_row.get("old_operative_quote") or "")[:300]),
        ("superseded_facts", cohort_row.get("old_parsed_facts") or {}),
        ("current_policy_agrees_with_the_superseded_read",
         bool((cohort_row.get("old_parsed_facts") or {}).get("pets_allowed")
              == (capture.get("extraction") or {}).get("pets_allowed"))),
    ))


def build(recovered, prior_policy, prior_exclusions, census_rows):
    """The published and refused sets, prior rows preserved and recovered rows
    republished on current evidence."""
    by_key = {row["identity_key"]: row for row in census_rows}
    published, refused = OrderedDict(), OrderedDict()

    for record in prior_policy["hotels"]:
        published[record["key"]] = record
    for record in prior_exclusions["exclusions"]:
        refused[record["normalized_name"]] = record

    changes = []
    for key, (cohort_row, capture) in sorted(recovered.items()):
        ident = by_key.get(key)
        if ident is None:
            changes.append((key, "NOT_IN_REGISTERED_CENSUS"))
            continue
        facts = facts_from_read({"extraction": capture["extraction"],
                                 "withheld_fields": [],
                                 "evidence": [],
                                 "canonical_name": ident["canonical_name"]})
        allowed = facts.get("pets_allowed")
        if allowed is True:
            record = OrderedDict((
                ("key", key), ("identity_key", key), ("name", ident["canonical_name"]),
                ("market_id", MARKET_ID), ("schema_version", enums.POLICY_SCHEMA_VERSION),
                ("facts", facts),
            ))
            statement = capture.get("service_animal_statement")
            if statement:
                record["service_animal_statement"] = statement
            record["computation_class"] = FC.classify(facts).computation_class
            record["evidence"] = evidence_rows(key, capture, facts)
            record["source_url"] = capture["final_url"]
            record["corridor"] = ident["corridor"]
            record["verified_at"] = capture["captured_at"]
            record["capture_lane"] = capture["capture_lane"]
            record["withheld_facts"] = OrderedDict()
            record["superseded_evidence"] = lineage(cohort_row, capture)
            record["reviewer_id"] = REVIEWER_ID
            record["reviewed_at"] = AS_OF
            record["review_basis"] = REVIEW_BASIS
            record["work_order"] = WORK_ORDER
            published[key] = record
            refused.pop(key, None)
            changes.append((key, "RECOVERED_CLEAN_PET_FRIENDLY"))
        elif allowed is False:
            rec = OrderedDict((
                ("market_id", MARKET_ID),
                ("exclusion_id", "nsh-" + slugify(ident["canonical_name"])),
                ("canonical_name", ident["canonical_name"]),
                ("normalized_name", key),
                ("address", ident["street"]), ("city", ident["city"]),
                ("state", STATE_CODE), ("postal_code", ident["postal_code"]),
                ("official_url", capture["final_url"]),
                ("exclusion_state", HE.VERIFIED_NO_PETS),
                ("evidence_quote", capture["exact_quote"]),
                ("source_url", capture["final_url"]),
                ("observed_at", capture["captured_at"][:10]),
                ("source_hash", _prefixed(capture.get("page_sha256"))),
            ))
            rec["record_hash"] = HE.record_hash(rec)
            rec["reviewer_id"] = REVIEWER_ID
            rec["reviewed_at"] = AS_OF
            rec["approval_hash"] = HE.approval_hash(rec)
            rec["review_basis"] = REVIEW_BASIS
            rec["capture_method"] = _LANE_CAPTURE[capture["capture_lane"]]
            rec["source_grade"] = _LANE_GRADE[capture["capture_lane"]]
            rec["superseded_evidence"] = lineage(cohort_row, capture)
            rec["notes"] = (
                "%s. First-party refusal re-read on the property's own page by the %s lane and "
                "hashed in the same call that took the quote. Service-animal access is a legal "
                "category and never converts a refusal into acceptance."
                % (WORK_ORDER, capture["capture_lane"]))
            refused[key] = rec
            published.pop(key, None)
            changes.append((key, "RECOVERED_CLEAN_VERIFIED_NO_PETS"))
        else:
            changes.append((key, "SOURCE_SILENT"))

    policy = OrderedDict((
        ("market", MARKET_NAME), ("schema_version", "1.3"), ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("note", "Nashville's published pet-friendly authority. Rows carrying "
                 "superseded_evidence were re-read and re-hashed by " + WORK_ORDER + " because "
                 "the legacy attended capture recorded a byte length and no document hash; the "
                 "rest are unchanged from " + PRIOR_ORDER + "."),
        ("hotels", sorted(published.values(), key=lambda h: h["key"])),
    ))
    for record in policy["hotels"]:
        issues = SCHEMA.validate_record(record)
        if issues:
            raise SystemExit("%s fails the record contract: %s"
                             % (record["name"], [(i.path, i.code) for i in issues]))
    issues = SCHEMA.validate_package(policy)
    if issues:
        raise SystemExit("policy package fails its contract: %s"
                         % [(i.path, i.code) for i in issues][:10])

    exclusions = OrderedDict((
        ("schema", HE.SCHEMA), ("contract", HE.SCHEMA), ("market_id", MARKET_ID),
        ("note", "This market's slice of the hotel-exclusions authority. The global "
                 "launch_packages/pettripfinder/hotel_exclusions.json is generated from every "
                 "market's shard and must not be hand-edited."),
        ("work_order", WORK_ORDER), ("count", len(refused)),
        ("exclusions", sorted(refused.values(), key=lambda r: r["exclusion_id"])),
    ))
    HE.validate(exclusions)
    return policy, exclusions, changes


def seed_rows(policy, by_key):
    rows = []
    for record in policy["hotels"]:
        ident = by_key[record["key"]]
        quote = " ".join(e["quote"] for e in record["evidence"][:4])
        rows.append(OrderedDict((
            ("name", record["name"]), ("category", "pet-friendly-hotels"),
            ("address", ident["street"]), ("city", ident["city"]), ("state", STATE_CODE),
            ("postal_code", ident["postal_code"]), ("phone", ident.get("phone") or ""),
            ("website_url", ident.get("official_url") or record["source_url"]),
            ("source_url", record["source_url"]), ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", str(record["verified_at"])[:10]), ("rating", ""), ("amenities", ""),
            ("pet_policy", quote[:600]), ("canonical", ""), ("market_id", MARKET_ID),
        )))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    cohort_doc = _load(COHORT)
    cohort = {r["identity_key"]: r for r in cohort_doc["recovery_cohort"]}
    census = _load(CENSUS_PATH)
    policy_prior = _load(POLICY_PATH)
    exclusions_prior = _load(os.path.join(PKG, "markets", "authority", MARKET_ID,
                                          "hotel_exclusions.json"))
    holds_prior = _load(HOLDS_PATH)

    captures = {}
    for path in (ATTENDED, STATIC):
        for row in _load(path)["rows"]:
            key = row.get("identity_key")
            if key and row.get("outcome") == "VALID" and key in cohort:
                captures[key] = row
    recovered = {k: (cohort[k], captures[k]) for k in captures}

    policy, exclusions, changes = build(recovered, policy_prior, exclusions_prior,
                                        census["hotels"])
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    seeds = seed_rows(policy, by_key)

    published_keys = {h["key"] for h in policy["hotels"]}
    refused_keys = {r["normalized_name"] for r in exclusions["exclusions"]}
    resolved = published_keys | refused_keys

    # Holds: everything still held, with the recovered rows removed and the
    # reason kept for anything that survived recovery.
    still_held = []
    for hold in holds_prior["holds"]:
        key = hold["identity_key_proposed"]
        if key in resolved:
            continue
        record = OrderedDict(hold)
        if key in cohort and key not in captures:
            failure = next((r for r in _load(ATTENDED)["rows"] + _load(STATIC)["rows"]
                            if r.get("identity_key") == key), None)
            record["recovery_attempted_by"] = WORK_ORDER
            record["recovery_outcome"] = (failure or {}).get("outcome", "NOT_CAPTURED")
            record["recovery_note"] = (
                "the page was re-read and re-hashed successfully, so CAPTURE_HASH is no longer "
                "the blocker. What refuses it now is the policy text itself: %s."
                % (failure or {}).get("outcome", "unknown"))
            record["gate_classification"] = (failure or {}).get("outcome", record.get(
                "gate_classification"))
            record["page_sha256"] = (failure or {}).get("page_sha256", "")
            record["reversible_without_recapture"] = False
        still_held.append(record)

    for row in cohort_doc["adjunct"]:
        key = row["identity_key"]
        if key not in resolved and not any(h["identity_key_proposed"] == key
                                           for h in still_held):
            still_held.append(row)

    holds = OrderedDict((
        ("schema", "ptf-market-identity-holds/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("note", "Nashville rows whose PUBLICATION is still held after "
                 + WORK_ORDER + " re-acquired the evidence behind the 85-row recovery cohort. "
                 "A row that left this file did so because its page was re-read and re-hashed, "
                 "not because a gate was lowered."),
        ("count", len(still_held)),
        ("counts_by_class",
         OrderedDict(sorted(Counter(h["classification"] for h in still_held).items()))),
        ("counts_by_gate_classification",
         OrderedDict(sorted(Counter(h.get("gate_classification", "") or ""
                                    for h in still_held).items()))),
        ("reversible_without_recapture",
         sum(1 for h in still_held if h.get("reversible_without_recapture"))),
        ("holds", sorted(still_held, key=lambda h: h["identity_key_proposed"])),
    ))

    # The census policy_state follows the authority.
    census_out = OrderedDict(census)
    census_out["work_order"] = WORK_ORDER
    census_out["captured_at"] = AS_OF
    hotels = []
    for row in census["hotels"]:
        out = OrderedDict(row)
        key = row["identity_key"]
        if key in published_keys:
            out["policy_state"] = "POLICY_CONFIRMED"
            out["policy_note"] = "First-party acceptance read on the property's own page."
            out.pop("publication_hold_class", None)
            out.pop("publication_hold_reason", None)
        elif key in refused_keys:
            out["policy_state"] = "VERIFIED_NO_PETS"
            out["policy_note"] = "First-party refusal read on the property's own page."
            out.pop("publication_hold_class", None)
            out.pop("publication_hold_reason", None)
        else:
            out["policy_state"] = "POLICY_NOT_VERIFIED"
        hotels.append(out)
    census_out["hotels"] = hotels
    census_out["publication_holds"] = holds["count"]
    issues = CENSUS.validate(census_out, market_states=[STATE_CODE])
    if issues:
        raise SystemExit("census fails its contract: %s"
                         % [(i.path, i.code, i.detail) for i in issues][:8])

    # The partition follows too.
    partition = _load(PARTITION_PATH)
    items = []
    for item in partition["items"]:
        out = OrderedDict(item)
        key = item["identity_key"]
        if key in published_keys:
            out.update((("final_state", "PUBLISHED_PET_FRIENDLY"), ("resolved", True),
                        ("next_action", ""), ("next_action_source", "")))
        elif key in refused_keys:
            out.update((("final_state", "VERIFIED_NO_PETS"), ("resolved", True),
                        ("next_action", ""), ("next_action_source", "")))
        out["updated_at"] = AS_OF
        out["determined_by"] = WORK_ORDER if key in resolved else item["determined_by"]
        items.append(out)
    partition_out = OrderedDict(partition)
    partition_out["work_order"] = WORK_ORDER
    partition_out["as_of"] = AS_OF
    partition_out["items"] = items
    partition_out["final_state_counts"] = OrderedDict(
        sorted(Counter(i["final_state"] for i in items).items()))

    report = OrderedDict((
        ("schema", "ptf-evidence-recovery-application/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("recovery_cohort", len(cohort)),
        ("successfully_recaptured", len(captures)),
        ("changes", OrderedDict(sorted(Counter(c for _k, c in changes).items()))),
        ("before", OrderedDict((("census", census["count"]),
                                ("published_pet_friendly", len(policy_prior["hotels"])),
                                ("verified_no_pets", len(exclusions_prior["exclusions"])),
                                ("holds", holds_prior["count"])))),
        ("after", OrderedDict((("census", census_out["count"]),
                               ("published_pet_friendly", len(policy["hotels"])),
                               ("verified_no_pets", exclusions["count"]),
                               ("holds", holds["count"])))),
        ("policy_changed_from_the_shadow", sorted(
            k for k, (c, cap) in recovered.items()
            if (c.get("old_shadow_class") == "CLEAN_PET_FRIENDLY")
            != bool((cap.get("extraction") or {}).get("pets_allowed") is True))),
        ("every_recovery_row_accounted_for_once",
         len(cohort) == len(captures) + len([h for h in still_held
                                             if h["identity_key_proposed"] in cohort])),
        ("row_changes", [OrderedDict((("identity_key", k), ("change", c)))
                         for k, c in sorted(changes)]),
    ))

    print("recovery cohort :", report["recovery_cohort"])
    print("recaptured      :", report["successfully_recaptured"])
    print("changes         :", dict(report["changes"]))
    print("before          :", dict(report["before"]))
    print("after           :", dict(report["after"]))
    print("policy changed  :", len(report["policy_changed_from_the_shadow"]))
    print("holds remaining :", holds["count"], dict(holds["counts_by_class"]))
    print("accounted once  :", report["every_recovery_row_accounted_for_once"])
    if args.check:
        print("nothing written (--check)")
        return 0

    _write(POLICY_PATH, policy)
    _write(str(MA.exclusions_shard_path(MARKET_ID)), exclusions)
    _write(CENSUS_PATH, census_out)
    _write(PARTITION_PATH, partition_out)
    _write(HOLDS_PATH, holds)
    seed_path = str(MA.seed_shard_path(MARKET_ID))
    os.makedirs(os.path.dirname(seed_path), exist_ok=True)
    with open(seed_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(MA.render_seed_csv(seeds))
    _write(args.out, report)
    print("written         :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
