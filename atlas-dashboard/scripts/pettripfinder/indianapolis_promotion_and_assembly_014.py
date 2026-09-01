# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 -- promote the reviewed shadow
into the pinned Indianapolis source state, apply the pending policy inventory,
re-author the release contract. Deployment-bearing; deploys nothing.

    python -m scripts.pettripfinder.indianapolis_promotion_and_assembly_014
    python -m scripts.pettripfinder.indianapolis_promotion_and_assembly_014 --write

FOUNDER AUTHORIZATION (this order): promote the shadow census, apply the
pending 11 PF + 3 no-pets, apply the Airport South explicit assignment,
rebuild Indianapolis release artifacts. NOT authorized: deploy, consume a
deployment authorization, touch another market, spend.

EVERY NUMBER IS DERIVED. The shadow is promoted whole, with its lineage blocks
(admission, retired_013, founder_rulings_013, every supersession) carried into
the pinned document; the 003 promotion block moves into promotion_history.

EVERY FACT IS READ BY THE CANONICAL READER OR WITHHELD. Each pending quote is
re-parsed with policy_reading.parse at application time. Where the reader
represents the source, the fact publishes; where it cannot, the field is
WITHHELD with a reason code and the source wording kept in the caveats:

  * the five Wyndham nightly per-pet fees read cleanly (15 / 20.00 / 25 / 25 /
    25 USD, per_night, per_pet);
  * "Pet Sanitation Fee is 50 USD if applicable" is CONDITIONAL and the
    schema has no condition for it -> other_charges SCHEMA_CANNOT_REPRESENT;
  * Baymont West's "100.00 USD refundable damage deposit" is a generic guest
    deposit the reader's frozen non-pet-purpose rule refuses -> withheld
    SOURCE_AMBIGUOUS, never published as a pet charge;
  * the six Extended Stay America blocks state TWO CEILINGS ("up to $25 (+tax)
    per day ... for the first six nights" then "not to exceed $15 ... per
    day"), and CEILING != PRICE is a founder rule; the reader reads one $15
    line and refuses the $25 -> pet_fee SOURCE_AMBIGUOUS. pets_allowed and the
    two-pet limit publish; the fee does not.
  * Baymont West's "Pets must not weigh more than 25 lbs each" is stated
    verbatim on the page; the reader's weight vocabulary does not read that
    phrasing (recorded in order 010). The pending inventory the founder
    authorised carries 25, and the quote is cited as its evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB       # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX               # noqa: E402
from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder import policy_migration as PM               # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR      # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS           # noqa: E402
from scripts.pettripfinder.contracts import enums                      # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA       # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify   # noqa: E402
from scripts.pettripfinder.release_contracts import (                  # noqa: E402
    contract_disagreements, derive_authority)

WORK_ORDER = "PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014"
MARKET_ID = "indianapolis-in"
OPERATOR = "jfields80"
REVIEWER = "PTF-FOUNDER-001"
AS_OF = "2026-09-01"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
PINNED = PKG / "identity_census" / "indianapolis-in.json"
SHADOW = PKG / "identity_census_admission" / "indianapolis-in.json"
MARKET_CONTRACT = PKG / "markets" / "indianapolis-in.json"
PACKAGE = PKG / "hotel_policy_facts_indianapolis-in.json"
PENDING = PKG / "indianapolis_in_pending_application_inventory_009.json"
EVID_008 = PKG / "indianapolis_in_shadow_policy_evidence_008.json"
EVID_009 = PKG / "indianapolis_in_shadow_policy_evidence_009.json"
PARTITION_004 = PKG / "indianapolis_in_final_partition_004.json"
PARTITION_014 = PKG / "indianapolis_in_final_partition_014.json"
CONTRACT = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / "indianapolis-in.json"
REPORT = PKG / "indianapolis_in_promotion_report_014.json"
OVERLAY = PKG / "markets" / "name_corrections" / "indianapolis-in.json"
AIRPORT_SOUTH = "woodspring suites indianapolis airport south"


class PromotionError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# io
# --------------------------------------------------------------------------- #

def _load(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    doc = json.loads(text, object_pairs_hook=OrderedDict)
    fmt = None
    for indent in (1, 2, 4):
        for ea in (True, False):
            for nl in ("\n", ""):
                if json.dumps(doc, indent=indent, ensure_ascii=ea) + nl == text:
                    fmt = (indent, ea, nl)
    return doc, (fmt or (1, False, "\n"))


def _dump(path, doc, fmt):
    Path(path).write_text(json.dumps(doc, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2],
                          encoding="utf-8", newline="\n")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digits(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --------------------------------------------------------------------------- #
# Phase 2 -- promote the shadow census
# --------------------------------------------------------------------------- #

def _chained_key_map(pinned, new):
    """003's key_map followed by 014's renames and merges."""
    fresh = OrderedDict()
    for h in new["hotels"]:
        for old in h.get("prior_census_identity_keys") or ():
            if old != h["identity_key"]:
                fresh[old] = h["identity_key"]
        for old in h.get("merged_in_013") or ():
            fresh[old] = h["identity_key"]
    for e in new.get("retired_013", []):
        target = (e.get("merged_into") or "").split(" (")[0].strip()
        if target and target in {h["identity_key"] for h in new["hotels"]}:
            fresh.setdefault(e["row"]["identity_key"], target)
    chained = OrderedDict()
    for old, mid in ((pinned.get("promotion") or {}).get("key_map") or {}).items():
        chained[old] = fresh.get(mid, mid)
    for old, tgt in fresh.items():
        chained.setdefault(old, tgt)
    return chained


def promote_census(shadow, pinned, market):
    new = json.loads(json.dumps(shadow), object_pairs_hook=OrderedDict)
    keys = [h["identity_key"] for h in new["hotels"]]
    if len(keys) != len(set(keys)):
        raise PromotionError("shadow carries duplicate identity keys")
    if new["count"] != len(keys):
        raise PromotionError("shadow count %s != rows %d" % (new["count"], len(keys)))
    retired = {e["row"]["identity_key"] for e in new.get("retired_013", [])}
    if retired & set(keys):
        raise PromotionError("a retired row is still active: %s" % sorted(retired & set(keys)))
    # every pinned key either survives, was retired with a ruling, or was renamed with lineage
    pinned_keys = {h["identity_key"] for h in pinned["hotels"]}
    renamed_from = set()
    for h in new["hotels"]:
        for old in h.get("prior_census_identity_keys") or ():
            if old != h["identity_key"]:
                renamed_from.add(old)
        was = (h.get("supersession") or {}).get("was") or {}
        if was.get("identity_key") and was["identity_key"] != h["identity_key"]:
            renamed_from.add(was["identity_key"])
    unaccounted = pinned_keys - set(keys) - retired - renamed_from
    if unaccounted:
        raise PromotionError("pinned identities with no lineage in the shadow: %s" % sorted(unaccounted))
    # address duplicates: none NEW versus the pinned census
    def akey(h):
        return (re.sub(r"[^a-z0-9]+", " ", (h.get("address") or "").lower()).strip(), str(h.get("postal_code") or ""))
    dup_new = {k for k, n in Counter(akey(h) for h in new["hotels"]).items() if n > 1 and k[0]}
    dup_old = {k for k, n in Counter(akey(h) for h in pinned["hotels"]).items() if n > 1 and k[0]}
    if dup_new - dup_old:
        raise PromotionError("new duplicate physical address introduced: %s" % sorted(dup_new - dup_old))
    # A display-name correction lives in the name_corrections OVERLAY, never in
    # the census: the census contract requires identity_key to derive from
    # canonical_name (PTF-INDIANAPOLIS-FINAL-ZERO-COST-CLEANUP-018 established
    # the overlay for exactly this). 013 recorded the founder's Wyndham West ->
    # Airport ruling on the row; the row's own name is restored here and the
    # correction is carried in the overlay by main().
    overlay_records = []
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    for h in new["hotels"]:
        if ptf_identity_key(h["canonical_name"]) != h["identity_key"]:
            nc = h.get("name_correction_013")
            if not nc:
                raise PromotionError("%s: name does not derive its key and no ruling explains it" % h["identity_key"])
            corrected = h["canonical_name"]
            h["canonical_name"] = nc["was"]["canonical_name"]
            h["display_name"] = nc["was"].get("display_name") or nc["was"]["canonical_name"]
            h["slug"] = nc["was"].get("slug") or _slug(h["canonical_name"])
            nc["applied_via"] = "markets/name_corrections/indianapolis-in.json (%s)" % WORK_ORDER
            overlay_records.append(OrderedDict((
                ("identity_key", h["identity_key"]),
                ("census_canonical_name", h["canonical_name"]),
                ("corrected_canonical_name", corrected),
                ("evidence_field", "page heading, attended read 2026-09-01"),
                ("property_code", ""),
                ("source_url", h.get("official_url", "")),
                ("why", "founder ruling IDR-012-006 (PTF-INDIANAPOLIS-FOUNDER-RULINGS-013): Wyndham retitled the "
                        "page 'Wyndham Indianapolis Airport' at the same street, postal and telephone; the census "
                        "keeps the discovered name and the reader is shown the page's"),
            )))
    new["overlay_records_014"] = [r["identity_key"] for r in overlay_records]
    issues = [i for i in CENSUS.validate(new, market_states=tuple(getattr(market, "states", ()) or ()))]
    if issues:
        raise PromotionError("promoted census does not validate: %s" % issues[:5])

    history = list(pinned.get("promotion_history") or [])
    if pinned.get("promotion"):
        history.append(pinned["promotion"])
    new["work_order"] = WORK_ORDER
    new["note"] = ("The PINNED Indianapolis identity census, promoted whole from the reviewed "
                   "shadow admission census by %s. Every supersession, retirement (retired_013) and "
                   "founder ruling travelled with it; nothing was re-derived. %s" % (WORK_ORDER, shadow.get("note", "")))
    new["promotion_history"] = history
    new["promotion"] = OrderedDict([
        ("what_this_is", "the founder-authorised promotion of the reviewed shadow census into the pinned production source census"),
        ("plan_work_order", WORK_ORDER), ("decided_by", "founder"), ("decided_on", AS_OF),
        ("from_count", len(pinned_keys)), ("to_count", len(keys)),
        ("source", "launch_packages/pettripfinder/identity_census_admission/indianapolis-in.json"),
        ("source_sha256", _sha(json.dumps(shadow, ensure_ascii=False, sort_keys=True))),
        ("retired", sorted(retired)), ("renamed_from", sorted(renamed_from)),
        # old key -> surviving key, CHAINED through the 003 map so every consumer
        # that rekeys the 002 pilot (indianapolis_recovery_005) still resolves.
        ("key_map", _chained_key_map(pinned, new)),
        ("orders_carried", ["PTF-INDIANAPOLIS-CENSUS-ADMISSION-002", "PTF-INDIANAPOLIS-APPLY-RULINGS-005",
                            "PTF-INDIANAPOLIS-ADDRESS-REVIEW-006", "PTF-INDIANAPOLIS-FREE-ROUTING-SCALE-007",
                            "PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012", "PTF-INDIANAPOLIS-FOUNDER-RULINGS-013"]),
        ("pinned_census_touched", True), ("deployment", "none; a separate founder authorization is required"),
    ])
    new.pop("overlay_records_014", None)
    return new, sorted(retired), sorted(renamed_from), overlay_records


# --------------------------------------------------------------------------- #
# Phase 3 -- Airport South explicit assignment
# --------------------------------------------------------------------------- #

def apply_airport_south(contract, census_rows):
    row = census_rows[AIRPORT_SOUTH]
    if row["postal_code"] != "46221" or row.get("assignment_basis") != "explicit":
        raise PromotionError("Airport South row is not the 007 state: %s / %s" % (row["postal_code"], row.get("assignment_basis")))
    airport = next(c for c in contract["corridors"] if c["corridor_id"] == "indianapolis-in__airport")
    if "46221" in airport["included_postal_codes"]:
        raise PromotionError("ZIP 46221 must not be widened")
    if AIRPORT_SOUTH not in airport["explicit_hotel_ids"]:
        airport["explicit_hotel_ids"].append(AIRPORT_SOUTH)
    if AIRPORT_SOUTH in airport.get("excluded_hotel_ids", []):
        raise PromotionError("Airport South is excluded from its own corridor")
    sentence = (" %s: the founder's IDR-005-002 ruling (PTF-INDIANAPOLIS-FREE-ROUTING-SCALE-007) is applied "
                "with the promotion that moved the row: WoodSpring Suites Indianapolis Airport South is assigned "
                "EXPLICITLY to the airport corridor at its current first-party address, 4545 Kentucky Ave, 46221. "
                "ZIP 46221 is not widened; no other hotel is admitted by this line." % WORK_ORDER)
    if WORK_ORDER not in contract["_boundary_note"]:
        contract["_boundary_note"] = contract["_boundary_note"] + sentence
    return contract


# --------------------------------------------------------------------------- #
# Phase 4/5 -- the fourteen pending records
# --------------------------------------------------------------------------- #

def _sa_quote(text: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+|\s+/\s+", text):
        if "service animal" in sentence.lower():
            return sentence.strip()
    return ""


def _money(cents):
    return [("amount_cents", int(cents)), ("currency", "USD")]


def project_facts(key: str, text: str, pending: Dict):
    """Facts from the canonical reader; withholdings where it cannot represent the source."""
    rd = PR.parse(text)
    facts = OrderedDict()
    withheld = OrderedDict()   # field -> (code, reason)
    notes = []
    if rd.pets_allowed is not True:
        raise PromotionError("%s: reader does not read pets_allowed True (%r)" % (key, rd.pets_allowed))
    facts["pets_allowed"] = True

    nightly = [c for c in rd.charges if c.basis in ("per_night", "per_day")]
    labelled = [c for c in rd.charges if not c.basis]
    if len(nightly) == 1:
        c = nightly[0]
        fee = OrderedDict(_money(c.amount_minor) + [("basis", "per_night")])
        if c.scope:
            fee["scope"] = c.scope
        if c.refundable is False:
            fee["refundable"] = False
        facts["pet_fee"] = fee
        exp = pending.get("fee_amount_usd")
        if exp is not None and int(round(float(exp) * 100)) != c.amount_minor:
            raise PromotionError("%s: reader fee %d != pending %s" % (key, c.amount_minor, exp))
    elif nightly:
        raise PromotionError("%s: more than one nightly charge read" % key)
    else:
        # ESA: two ceilings, one read as a labelled $15, the $25 refused as non-pet purpose
        withheld["pet_fee"] = (
            enums.SOURCE_AMBIGUOUS,
            "the block states two CEILINGS, not a price: 'up to a $25 (+ tax) per day non-refundable "
            "cleaning fee for the first six (6) nights, per pet' and thereafter 'not to exceed $15 ... per "
            "day, per pet'. CEILING != PRICE is a founder rule; the canonical reader reads a single $15 "
            "line and refuses the $25 line, which would publish the lower rung as the nightly fee. "
            "Withheld rather than published wrong; the wording is preserved here.")
    sanitation = [c for c in labelled if "sanitation" in c.quote.lower()]
    if sanitation:
        withheld["other_charges"] = (
            enums.SCHEMA_CANNOT_REPRESENT,
            "'%s' is stated CONDITIONALLY ('if applicable' / 'if required'). Schema 1.3 conditions "
            "are stay_length_range and pet_count_range, so a damage-conditional charge has nowhere "
            "to live, and publishing it unconditioned would tell every guest they owe it." % sanitation[0].quote)
    if re.search(r"damage deposit", text, re.I) and rd.excluded_amounts:
        withheld["other_charges"] = (
            enums.SOURCE_AMBIGUOUS,
            "'A 100.00 USD refundable damage deposit is required at check-in' names no pet: the "
            "reader's frozen non-pet-purpose rule (damage deposit) refuses it as a pet charge, and "
            "whether Wyndham means a pet deposit is not stated.")

    count = rd.pet_count_limit
    if count is None and pending.get("pet_count_limit"):
        raise PromotionError("%s: pending states a count the reader does not read" % key)
    if count is not None:
        facts["pet_count_limit"] = int(count)

    if rd.weight_value is not None:
        facts["weight_limit"] = OrderedDict((("value", float(rd.weight_value)), ("unit", "lb"),
                                             ("operator", "lte"), ("scope", "per_pet")))
    elif pending.get("individual_weight_limit_lbs"):
        m = re.search(r"must not weigh more than (\d+) lbs each", text, re.I)
        if not m or int(m.group(1)) != int(pending["individual_weight_limit_lbs"]):
            raise PromotionError("%s: pending weight not found verbatim" % key)
        facts["weight_limit"] = OrderedDict((("value", float(m.group(1))), ("unit", "lb"),
                                             ("operator", "lte"), ("scope", "per_pet")))
        notes.append("weight_limit is read from the verbatim sentence '%s'; the canonical reader's "
                     "weight vocabulary does not parse the 'must not weigh more than' phrasing "
                     "(recorded in PTF-GENERIC-FEE-READER-USD-SUFFIX-FIX-010) and the founder-authorised "
                     "pending inventory carries the same value" % m.group(0))

    species = OrderedDict()
    if rd.cats_refused_quote:
        species["cats"] = enums.SPECIES_PROHIBITED
    if rd.dogs_only_quote:
        species["dogs"] = enums.SPECIES_ACCEPTED
    if species:
        facts["species"] = species

    if re.search(r"no longer than 36 inches", text, re.I):
        withheld["dimension_constraints"] = (
            enums.SCHEMA_CANNOT_REPRESENT,
            "'pets can be no longer than 36 inches and no taller than 36 inches' -- a size rule the "
            "schema has no field for; preserved in wording.")
    sa = _sa_quote(text)
    return facts, withheld, notes, sa, rd


def _evidence(fields, quote, url, sha, kind, method, captured_at):
    entries = []
    for field in fields:
        entry = OrderedDict((
            ("field", field), ("quote", quote), ("source_url", url),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", "sha256:%s" % sha), ("artifact_kind", kind),
            ("captured_at", captured_at), ("capture_method", method),
            ("source_grade", "PT1_FIRST_PARTY")))
        entry["evidence_ref"] = PM.evidence_ref_for(entry)
        entries.append(entry)
    return entries


def build_record(pend: Dict, census_row: Dict, text: str, kind: str, method: str) -> Dict:
    key = pend["identity_key"]
    facts, withheld, notes, sa, rd = project_facts(key, text, pend.get("facts") or {})
    fields = ["pets_allowed"]
    if "pet_fee" in facts:
        fields += ["pet_fee", "fee_basis", "fee_scope"]
    for f in ("pet_count_limit", "weight_limit", "species"):
        if f in facts:
            fields.append(f)
    if sa:
        fields.append("service_animal_statement")
    captured_at = pend["captured_at"][:10]
    entries = _evidence(fields, text, pend["canonical_url"], pend["document_sha256"], kind, method, captured_at)
    record = OrderedDict((
        ("key", key), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", entries), ("evidence_count", len(entries)),
        ("evidence_quote", text), ("source_url", pend["canonical_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", captured_at), ("verified_at", captured_at),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", pend["document_sha256"]),
        ("worker_routing_version", ""), ("worker_validator_version", ""),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("identity_key", key), ("market_id", MARKET_ID),
    ))
    if sa:
        record["service_animal_statement"] = OrderedDict((("stated", True), ("charges_stated", SA.charges_stated(sa)), ("quote", sa)))
    # The Indianapolis envelope every earlier record carries (017/018 tests pin it):
    # the founder decision and reviewer on the record itself, plus the two
    # honesty lists the projection layer writes.
    record["non_inferences"] = [
        "weight_limit.operator: 'must not weigh more than' / 'or less' are recorded as lte per pet only where the source states the ceiling per pet",
        "species: a surface that names one refused species says nothing about the others; nothing is defaulted",
        "other_charges: a conditional or generic charge is withheld with its wording, never published unconditioned",
    ] + (["pet_fee: two stated ceilings are not a price; withheld rather than published as the lower rung"] if "pet_fee" in withheld else [])
    record["founder_decision"] = enums.APPROVED_AFTER_CURRENT_REVIEW
    record["founder_reviewer_id"] = REVIEWER
    record["founder_reviewed_at"] = AS_OF
    record["projection_notes"] = ["%s: facts re-read by policy_reading.parse at application; see approval.caveats" % WORK_ORDER] + notes
    record["computation_class"] = classify(facts).computation_class
    if withheld:
        record["withheld_fields"] = OrderedDict(
            (field, OrderedDict((("reason_code", code), ("reason", why), ("evidence_refs", [entries[0]["evidence_ref"]]))))
            for field, (code, why) in withheld.items())
    caveats = [
        "FOUNDER AUTHORIZATION (%s): apply the pending Indianapolis policy inventory of "
        "PTF-INDIANAPOLIS-ATTENDED-POLICY-PASS-009 (ESA rows from PTF-INDIANAPOLIS-FREE-POLICY-PASS-008)." % WORK_ORDER,
        "Every fact was re-read by the canonical reader (policy_reading.parse) at application time; "
        "fields the reader cannot represent are withheld with a reason, never inferred.",
        ("Attended Chrome render, $0: the artifact digest binds the canonical URL, the rendered property "
         "address and the rendered policy text (order 009's digest basis) -- a text_extract artifact."
         if kind == "text_extract" else
         "Deterministic free HTTP fetch, $0: the artifact digest is the SHA256 of the served page."),
    ] + notes
    record["approval"] = OrderedDict((
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW), ("operator", OPERATOR),
        ("approval_date", AS_OF), ("caveats", caveats),
        ("record_hash", PM.record_hash(record)), ("evidence_hash", PM.evidence_hash(entries)),
    ))
    return record


REFUSALS = ("not allowed", "no other pets", "no pets", "prohibited", "not permitted", "do not allow")


def build_exclusion(pend: Dict, census_row: Dict) -> Dict:
    key = pend["identity_key"]
    quote = pend["exact_quote"]
    if not any(p in quote.lower() for p in REFUSALS):
        raise PromotionError("%s: refusal is not affirmative" % key)
    rd = PR.parse(quote)
    if rd.pets_allowed is not False:
        raise PromotionError("%s: reader does not read the refusal (%r)" % (key, rd.pets_allowed))
    record = OrderedDict((
        ("exclusion_id", "ii-" + key.replace(" ", "-")),
        ("canonical_name", census_row["canonical_name"]), ("normalized_name", key),
        ("address", census_row.get("address", "")), ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")), ("postal_code", census_row.get("postal_code", "")),
        ("official_url", pend["canonical_url"]),
        ("exclusion_state", enums.VERIFIED_NO_PETS),
        ("evidence_quote", quote), ("evidence_context", quote),
        ("source_url", pend["canonical_url"]), ("observed_at", pend["captured_at"][:10]),
        ("source_hash", "sha256:%s" % pend["document_sha256"]),
        ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
        ("notes", "affirmative, property-specific refusal in the property's own rendered policy; the "
                  "service-animal sentence beside it is a legal access category and is never read as a "
                  "pet permission or as the refusal itself. Captured attended at $0 by "
                  "PTF-INDIANAPOLIS-ATTENDED-POLICY-PASS-009; applied by %s." % WORK_ORDER),
        ("market_id", MARKET_ID),
        ("decision_source", OrderedDict((
            ("work_order", WORK_ORDER),
            ("ledgers", ["PTF-INDIANAPOLIS-ATTENDED-POLICY-PASS-009", WORK_ORDER]),
            ("decided_by", REVIEWER),
            ("decision_basis", "founder authorization of the pending clean verified-no-pets inventory in "
                               "%s; the exclusion restates that ruling and adds no finding of its own" % WORK_ORDER)))),
    ))
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# --------------------------------------------------------------------------- #
# Phase 6 -- partition + contract
# --------------------------------------------------------------------------- #

def build_partition(census, published, excluded, prior):
    items = []
    for h in census["hotels"]:
        k = h["identity_key"]
        if k in published:
            state = enums.PUBLISHED_PET_FRIENDLY
        elif k in excluded:
            state = enums.VERIFIED_NO_PETS
        elif k in prior and prior[k]["final_state"] not in enums.TERMINAL_STATES:
            state = prior[k]["final_state"]
        else:
            state = enums.AWAITING_POLICY_OBSERVATION if h.get("official_url") else enums.AWAITING_OFFICIAL_URL
        items.append(CPB.partition_item(
            identity_key=k, canonical_name=h["canonical_name"], slug=h.get("slug") or _slug(h["canonical_name"]),
            city=h.get("city", ""), state=h.get("state", ""), postal_code=h.get("postal_code", ""),
            final_state=state,
            next_action_source=(prior.get(k, {}).get("next_action_source") or "carried from the promoted census by %s" % WORK_ORDER),
            determined_by=WORK_ORDER, updated_at=AS_OF, official_url=h.get("official_url", "")))
    return CPB.partition_document(
        MARKET_ID, items, as_of=AS_OF,
        note=("The Indianapolis final partition over the 263-identity census promoted by %s: 67 published, "
              "the verified-no-pets registry as the refusal authority, every other identity carrying the "
              "blocker state the 004 partition recorded or, for identities admitted since, the state its "
              "own row implies. Not mapped in build_market_manifest: this market records no "
              "OUT_OF_CURRENT_CATEGORY identity, so its unresolved count is derived exactly by subtraction "
              "(PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004), and this document is the record of the same fact." % WORK_ORDER),
        source_authorities=["identity_census/indianapolis-in.json", "hotel_policy_facts_indianapolis-in.json",
                            "markets/authority/indianapolis-in/hotel_exclusions.json", PARTITION_004.name])


def reauthor_contract(contract):
    derived = derive_authority(MARKET_ID)
    recon = dict(derived.reconciliation())
    contract["description"] = (
        "Deterministic release-gate contract for the PetTripFinder Indianapolis market through %s. "
        "Calibrated to THIS market's committed authority; every number is derived from the authority "
        "files, none is typed." % WORK_ORDER)
    contract["deployment_authorization"] = OrderedDict((
        ("grants_deployment", False), ("asserts_market_complete", False),
        ("means", "A passing contract means this market's assembled package is STRUCTURALLY deployable: "
                  "its authority files agree, its routes match its reviewed inventory, no held identity "
                  "leaks, and every publish gate holds. It is not a deployment authorization: %s promoted "
                  "the census and applied the pending policy inventory and deployed nothing; the "
                  "authorization that put the previous 56-profile Indianapolis live was signed against "
                  "the contract this one replaces and cannot authorise this state. %d of %d confirmed "
                  "identities remain unresolved." % (WORK_ORDER, recon["unresolved"], recon["confirmed_identities"])),
    ))
    pkg = contract["policy_package"]
    pkg["expected_sha256"] = derived.policy_package_sha256
    pkg["expected_schema_version"] = derived.policy_package_schema_version
    pkg["expected_record_count"] = derived.policy_package_record_count
    surface = contract["public_surface"]
    surface["seed_hotel_rows"] = derived.seed_hotel_rows
    surface["public_hotel_profile_count"] = derived.published_hotel_profiles
    surface["excluded_public_profile_count"] = derived.excluded_public_profiles
    routes = contract["routes"]
    routes["hotel_route_count"] = derived.hotel_route_count
    routes["published_corridor_route_count"] = derived.corridor_route_count
    contract["reconciliation"] = OrderedDict(
        [(f, recon[f]) for f in ("confirmed_identities", "published_pet_friendly", "verified_no_pets", "resolved", "unresolved")]
        + [("note", "%s: census promoted 257 -> %d (five retirements and one rebrand-successor rename with "
                    "lineage, from PTF-INDIANAPOLIS-FOUNDER-RULINGS-013), 11 pending pet-friendly records and 3 "
                    "verified-no-pets exclusions applied from the 008/009 zero-cost captures. resolved = "
                    "published + verified_no_pets; unresolved = confirmed - resolved, exact because this market "
                    "records no OUT_OF_CURRENT_CATEGORY identity."
                    % (WORK_ORDER, recon["confirmed_identities"]))])
    contract["identity_census"]["expected_count"] = derived.confirmed_identities
    problems = contract_disagreements(contract, derived)
    return contract, derived, problems


# --------------------------------------------------------------------------- #

def finish() -> int:
    """Partition, contract and report over the files --write left on disk.

    Separate from --write because the contract derivation joins policy records
    to the GLOBAL seed inventory, which build_global_authority regenerates from
    the shards between the two steps."""
    census, _ = _load(PINNED)
    package, _ = _load(PACKAGE)
    if len(census["hotels"]) != 263 or len(package["hotels"]) != 67:
        raise PromotionError("finish expects the written state (263 / 67), found %d / %d"
                             % (len(census["hotels"]), len(package["hotels"])))
    shard = MA.load_market_exclusions_document(MARKET_ID)
    published = {h["identity_key"] for h in package["hotels"]}
    excluded = {e["normalized_name"] for e in shard["exclusions"] if e.get("exclusion_state") == enums.VERIFIED_NO_PETS}
    prior_partition = {i["identity_key"]: i for i in _load(PARTITION_004)[0]["items"]}
    partition = build_partition(census, published, excluded, prior_partition)
    CPB.write_json(PARTITION_014, partition)
    contract, cfmt = _load(CONTRACT)
    contract, derived, problems = reauthor_contract(contract)
    print("release-contract disagreements : %d" % len(problems))
    for p in problems:
        print("   ", p)
    if problems:
        raise PromotionError("re-authored contract still disagrees")
    _dump(CONTRACT, contract, cfmt)
    new_keys = [h["identity_key"] for h in package["hotels"][56:]]
    summary = OrderedDict([
        ("pinned_before", 257), ("pinned_after", len(census["hotels"])),
        ("retired", census["promotion"]["retired"]), ("renamed_from", census["promotion"]["renamed_from"]),
        ("records_applied", new_keys),
        ("exclusions_applied", [e["normalized_name"] for e in shard["exclusions"][34:]]),
        ("withheld", OrderedDict((h["identity_key"], list((h.get("withheld_fields") or {}).keys())) for h in package["hotels"][56:])),
        ("package_count", len(package["hotels"])), ("exclusion_count", shard["count"]),
        ("seed_rows", len(MA.load_market_seed_rows(MARKET_ID))),
        ("partition_counts", partition["final_state_counts"]),
        ("reconciliation", derived.reconciliation()),
        ("policy_package_sha256", derived.policy_package_sha256),
        ("hotel_routes", derived.hotel_route_count), ("corridor_routes", derived.corridor_route_count),
    ])
    Path(REPORT).write_text(json.dumps(OrderedDict([("schema", "ptf-promotion-report/1.0"), ("work_order", WORK_ORDER),
                                                    ("market_id", MARKET_ID), ("as_of", AS_OF), ("decided_by", "founder"),
                                                    ("paid_provider_calls", 0), ("usd_spent", 0.0), ("deployment_performed", False),
                                                    ("summary", summary)]), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    print("WROTE partition 014, release contract, promotion report")
    print(json.dumps(dict(derived.reconciliation()), ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--finish", action="store_true",
                        help="after --write and build_global_authority --write: rebuild the partition, "
                             "re-author the release contract, write the report")
    args = parser.parse_args(argv)
    from scripts.pettripfinder.markets import load_markets, market_by_id
    market = market_by_id(load_markets(), MARKET_ID)
    if args.finish:
        return finish()

    shadow, sfmt = _load(SHADOW)
    pinned, pfmt = _load(PINNED)
    mcontract, mfmt = _load(MARKET_CONTRACT)
    package, kfmt = _load(PACKAGE)
    pending, _ = _load(PENDING)
    e008 = {r["identity_key"]: r for r in _load(EVID_008)[0]["records"]}
    prior_partition = {i["identity_key"]: i for i in _load(PARTITION_004)[0]["items"]}
    if len(pinned["hotels"]) != 257 or len(shadow["hotels"]) != 263:
        raise PromotionError("starting state is not 257 pinned / 263 shadow")

    # Phase 2
    census, retired, renamed_from, overlay_records = promote_census(shadow, pinned, market)
    rows = {h["identity_key"]: h for h in census["hotels"]}
    overlay, ofmt = _load(OVERLAY)
    if any(r["identity_key"] in {o["identity_key"] for o in overlay["records"]} for r in overlay_records):
        raise PromotionError("overlay already carries a correction for a 014 row")
    overlay["records"] = list(overlay["records"]) + overlay_records
    overlay["count"] = len(overlay["records"])
    overlay["authorised_by"] = overlay.get("authorised_by", "") + "; %s (IDR-012-006)" % WORK_ORDER
    # Phase 3
    mcontract = apply_airport_south(mcontract, rows)

    # Phase 4/5
    clean_pf = pending["CLEAN_PET_FRIENDLY"]
    clean_np = pending["CLEAN_VERIFIED_NO_PETS"]
    if len(clean_pf) != 11 or len(clean_np) != 3 or pending["FOUNDER_EXCEPTION"]:
        raise PromotionError("pending inventory is %d/%d/%d" % (len(clean_pf), len(clean_np), len(pending["FOUNDER_EXCEPTION"])))
    published = {h["identity_key"] for h in package["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"] if e.get("exclusion_state") == enums.VERIFIED_NO_PETS}
    records, exclusions = [], []
    for pend in clean_pf:
        key = pend["identity_key"]
        if key not in rows:
            raise PromotionError("%s not in the promoted census" % key)
        if key in published or key in excluded:
            raise PromotionError("%s already in authority" % key)
        row = rows[key]
        if not row.get("official_url") or EX.canonical_url(row["official_url"]) != EX.canonical_url(pend["canonical_url"]):
            raise PromotionError("%s: census route %r != pending %r" % (key, row.get("official_url"), pend["canonical_url"]))
        if pend.get("source_order") == "009":
            text, kind, method = pend["exact_quote"], enums.ARTIFACT_TEXT_EXTRACT, "attended_chrome_render"
        else:
            blocks = e008[key]["evidence_blocks"]
            text = next(b["text"] for b in blocks if b.get("kind") == "property_pet_policy_block")
            text = text.replace("&rsquo;", "'").replace("&nbsp;", " ").strip()
            kind, method = enums.ARTIFACT_RENDERED_HTML, "deterministic_fetch"
            if e008[key]["document_sha256"] != pend["document_sha256"]:
                raise PromotionError("%s: evidence sha mismatch" % key)
        records.append(build_record(pend, row, text, kind, method))
    for pend in clean_np:
        key = pend["identity_key"]
        if key not in rows or key in published or key in excluded:
            raise PromotionError("%s: not applicable as an exclusion" % key)
        exclusions.append(build_exclusion(pend, rows[key]))
    keys = [r["identity_key"] for r in records]
    if len(set(keys)) != 11 or set(keys) & {e["normalized_name"] for e in exclusions}:
        raise PromotionError("duplicate or overlapping identities in the applied set")
    slugs = Counter(_slug(h["name"]) for h in package["hotels"] + records)
    if any(n > 1 for n in slugs.values()):
        raise PromotionError("duplicate profile route slug: %s" % [s for s, n in slugs.items() if n > 1])

    package["hotels"] = package["hotels"] + records
    package["count"] = len(package["hotels"])
    # The release-gate contract is policy_schema.validate_package (0 issues on
    # the committed package). validate_migrated additionally demands a
    # computation_class, which this market's 56 earlier records never carried;
    # the NEW records carry one and are held to it on their own.
    from scripts.pettripfinder.contracts import policy_schema as PS
    gate_issues = list(PS.validate_package(package))
    if gate_issues:
        raise PromotionError("package fails the schema gate: %s" % gate_issues[:10])
    only_new = OrderedDict(package)
    only_new["hotels"] = records
    problems = PM.validate_migrated(only_new)
    if problems:
        raise PromotionError("new records do not validate: %s" % problems[:10])
    # The shard is kept SORTED by normalized_name, the order the freeze tests
    # compare against; appending would break it.
    shard["exclusions"] = sorted(list(shard["exclusions"]) + exclusions, key=lambda e: e["normalized_name"])
    shard["count"] = len(shard["exclusions"])
    validated = EX.validate(shard)          # returns the validated rows; raises on a defect
    if len(validated) != shard["count"]:
        raise PromotionError("exclusion shard validated %d of %d rows" % (len(validated), shard["count"]))

    # seed shard
    seed_rows = MA.load_market_seed_rows(MARKET_ID)
    seed_names = {r["name"] for r in seed_rows}
    for r in records:
        h = rows[r["identity_key"]]
        if h["canonical_name"] in seed_names:
            raise PromotionError("seed row already present for %s" % h["canonical_name"])
        seed_rows.append(OrderedDict((
            ("name", h["canonical_name"]), ("category", "pet-friendly-hotels"),
            ("address", h.get("address", "")), ("city", h.get("city", "")), ("state", h.get("state", "")),
            ("postal_code", h.get("postal_code", "")), ("phone", _digits(h.get("phone"))),
            ("website_url", h["official_url"]), ("source_url", h["official_url"]),
            ("source_type", "OFFICIAL_PROPERTY"), ("observed_at", r["verified_at"]),
            ("rating", ""), ("amenities", ""), ("pet_policy", "pets allowed"), ("canonical", ""),
            ("market_id", MARKET_ID))))

    summary = OrderedDict([
        ("pinned_before", 257), ("pinned_after", len(census["hotels"])),
        ("retired", retired), ("renamed_from", renamed_from),
        ("records_applied", keys), ("exclusions_applied", [e["normalized_name"] for e in exclusions]),
        ("withheld", OrderedDict((r["identity_key"], list((r.get("withheld_fields") or {}).keys())) for r in records)),
        ("package_count", package["count"]), ("exclusion_count", shard["count"]), ("seed_rows", len(seed_rows)),
    ])
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    _dump(PINNED, census, pfmt)
    shadow["promoted_into_pinned"] = OrderedDict((("work_order", WORK_ORDER), ("at", AS_OF), ("count", len(census["hotels"]))))
    _dump(SHADOW, shadow, sfmt)
    _dump(MARKET_CONTRACT, mcontract, mfmt)
    _dump(OVERLAY, overlay, ofmt)
    _dump(PACKAGE, package, kfmt)
    MA.exclusions_shard_path(MARKET_ID).write_text(MA.render_json(shard), encoding="utf-8", newline="\n")
    MA.seed_shard_path(MARKET_ID).write_text(MA.render_seed_csv(seed_rows), encoding="utf-8", newline="")
    print("WROTE census, shadow marker, market contract, package, exclusions shard, seed shard")

    # partition + contract (contract derivation reads the files just written)
    partition = build_partition(census, set(published) | set(keys), excluded | {e["normalized_name"] for e in exclusions}, prior_partition)
    CPB.write_json(PARTITION_014, partition)
    contract, cfmt = _load(CONTRACT)
    contract, derived, problems = reauthor_contract(contract)
    print("release-contract disagreements : %d" % len(problems))
    for p in problems:
        print("   ", p)
    if problems:
        raise PromotionError("re-authored contract still disagrees")
    _dump(CONTRACT, contract, cfmt)
    summary["partition_counts"] = partition["final_state_counts"]
    summary["reconciliation"] = derived.reconciliation()
    summary["policy_package_sha256"] = derived.policy_package_sha256
    Path(REPORT).write_text(json.dumps(OrderedDict([("schema", "ptf-promotion-report/1.0"), ("work_order", WORK_ORDER),
                                                    ("market_id", MARKET_ID), ("as_of", AS_OF), ("decided_by", "founder"),
                                                    ("paid_provider_calls", 0), ("usd_spent", 0.0), ("deployment_performed", False),
                                                    ("summary", summary)]), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    print("WROTE partition 014, release contract, promotion report")
    print(json.dumps(dict(derived.reconciliation()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
