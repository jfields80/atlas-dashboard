"""PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 -- apply Pass 3.

    python -m scripts.pettripfinder.cincinnati_pass3_decision_application_004
    python -m scripts.pettripfinder.cincinnati_pass3_decision_application_004 --write

WHAT THE FOUNDER AUTHORISED
---------------------------
A BLOCK of 57 clean candidates -- 47 pet-friendly, 10 verified-no-pets -- plus
eight individually reasoned rulings on the exceptions Pass 3 could not settle
from the source alone. The block was authorised on the condition that this
module verify it mechanically first, and remove from it any candidate that
fails; all 57 passed, so the block is applied whole.

The eight rulings are recorded here VERBATIM as the founder gave them, and the
disposition of each is derived from the ruling rather than restated. Two of the
eight publish nothing:

  #1 Extended Stay America Cincinnati Fairfield -- RENAME, no policy. The
     building at 9651 Seward Rd now trades as Studio 6 Extended Stay Fairfield.
     The identity is renamed here; its policy waits for a clean recapture
     against the new name, because publishing the Studio 6 page's terms under
     the ESA name would cite a name that page does not make.
  #2 Great Wolf Lodge -- HOLD. The founder declined to lower this market's
     no-pets evidentiary standard for a bare structured-data flag. The
     observation is preserved as evidence; the identity stays unresolved.

WHAT THIS MODULE WILL NOT DO
----------------------------
It does not widen a shared reader to accommodate a market decision. Ruling #4
is the live example: the founder ruled that "Fee Exempts: ADA Service Animals
Only" keeps charges_stated = not_addressed and that
``contracts.service_animal`` must NOT be widened here. So the quote is
preserved for a future generic review and the classifier is untouched -- a
market application is the wrong place to teach a global reader a new pattern.

SPECIES KEYS ARE PLURAL
-----------------------
``canonical_view`` reads ``species["dogs"]`` and ``species["cats"]``. The 21
records already published in this market use the SINGULAR "dog"/"cat", so their
species never reach a public surface. Every record written here uses the plural
form the display projection actually reads. The eight existing records are NOT
rewritten -- that is founder-approved authority and a separate ruling -- and the
defect is reported instead.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX            # noqa: E402
from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder import policy_migration as PM            # noqa: E402
from scripts.pettripfinder.contracts import enums                   # noqa: E402
from scripts.pettripfinder.contracts import policy_schema           # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004"
MARKET_ID = "cincinnati-oh"
OPERATOR = "jfields80"
DECISION_DATE = "2026-08-29"
OBSERVED_AT = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
DECISIONS = REPORTS / "cincinnati_pass3_founder_decisions_004.json"

#: The founder's eight rulings, as given. ``publishes`` says whether the ruling
#: results in a policy record; ``changes`` is what the founder altered from the
#: disposition Pass 3 proposed.
RULINGS = OrderedDict((
    ("extended stay america cincinnati fairfield", {
        "founder_decision": "RENAME_REBRAND_DO_NOT_PUBLISH_YET",
        "publishes": False,
        "ruling": "Approve the identity determination that the former Extended "
                  "Stay America property at 9651 Seward Rd is now Studio 6 "
                  "Extended Stay Fairfield, OH - Cincinnati. Do not publish "
                  "the Studio 6 pet policy against the old ESA identity. "
                  "Update the identity through the sanctioned rebrand/identity "
                  "path and place the renamed property into the next clean "
                  "recapture/application pass. Do not merge it with Studio 6 "
                  "Cincinnati Springdale.",
        "changes": "Pass 3 proposed IDENTITY_MISMATCH with no disposition. The "
                   "founder settled the identity and deferred the policy.",
        "rename_to": "Studio 6 Extended Stay Fairfield, OH - Cincinnati",
    }),
    ("great wolf lodge cincinnati mason", {
        "founder_decision": "HOLD_FOR_PROSE_EVIDENCE",
        "publishes": False,
        "ruling": "Do NOT publish VERIFIED_NO_PETS from the bare JSON-LD "
                  "petsAllowed: false alone. Preserve the structured "
                  "observation as evidence, but keep the property unresolved "
                  "until a property-specific prose statement or equivalently "
                  "clear first-party policy surface is captured. Do not lower "
                  "the Cincinnati no-pets evidentiary standard for this row.",
        "changes": "Pass 3 proposed VERIFIED_NO_PETS and flagged it. The "
                   "founder declined it and kept the standard.",
    }),
    ("hampton inn and suites cincinnati kenwood", {
        "founder_decision": "APPROVE_PARTIAL_PUBLICATION",
        "publishes": True,
        "ruling": "Publish only the fields directly and completely supported "
                  "by this property's own source: pets_allowed true, pet_fee "
                  "$75, basis per stay / non-refundable. WITHHOLD species, "
                  "pet_count_limit, fee tiers derived from the truncated text, "
                  "and weight_limit. Do not complete 'dog/cat onl' from a "
                  "sibling property's wording.",
        "changes": "None -- the founder affirmed the proposed withholding.",
    }),
    ("hampton inn and suites newport cincinnati", {
        "founder_decision": "APPROVE_PUBLISH_STRUCTURED",
        "publishes": True,
        "ruling": "Approve pets_allowed true, dogs accepted, cats prohibited, "
                  "pet_count_limit 2, fee tier $75 for 1-3 nights, fee tier "
                  "$125 for 4-7 nights. Do not invent an 8+ night rate. For "
                  "'Fee Exempts: ADA Service Animals Only' do NOT widen the "
                  "shared service-animal classifier in this market "
                  "application; keep charges_stated = not_addressed and "
                  "preserve the exact quote for a future generic classifier "
                  "review.",
        "changes": "None. The founder upheld the conservative reading this "
                   "pass deferred to and forbade widening the shared reader.",
    }),
    ("hilton cincinnati netherland plaza", {
        "founder_decision": "APPROVE_WITH_CHANGE",
        "publishes": True,
        "ruling": "Approve $50 as a NON-REFUNDABLE PET FEE, using the "
                  "structured Hilton field as the charge classification: "
                  "pets_allowed true, pet_fee $50, non-refundable true, "
                  "weight_limit 25 lbs. Treat the prose phrase 'Non Refundable "
                  "Pet Deposit' as conflicting terminology, not as evidence of "
                  "a refundable deposit. Do not publish a separate deposit. "
                  "Preserve both conflicting source strings in evidence.",
        "changes": "Pass 3 withheld BOTH fee and deposit. The founder resolved "
                   "the conflict in favour of the structured field and "
                   "released the fee.",
    }),
    ("homewood suites by hilton cincinnati mason", {
        "founder_decision": "APPROVE_WITH_CHANGE",
        "publishes": True,
        "ruling": "Approve pets_allowed true, dogs and cats, weight_limit 75 "
                  "lbs, pet_fee headline $75, $75 for 1-4 nights and $125 for "
                  "5+ nights. WITHHOLD pet_count_limit unless independently "
                  "supported. Preserve the structured $125 headline conflict "
                  "in evidence, but use $75 as the entry/headline fee because "
                  "the property's own tiered prose establishes $75 as the "
                  "applicable short-stay charge.",
        "changes": "Pass 3 withheld the headline fee. The founder released it "
                   "at $75, the short-stay rate, over the $125 field.",
    }),
    ("days inn florence", {
        "founder_decision": "APPROVE_PUBLISH_STRUCTURED",
        "publishes": True,
        "ruling": "Approve pets_allowed true, pet_count_limit 2, $25 per pet "
                  "per night. Carry VERBATIM in general restrictions 'Pets "
                  "Allowed for max of 5 day stay'. Do not drop the five-day "
                  "pet-stay restriction simply because there is no dedicated "
                  "structured field. WITHHOLD the $200 sanitation fee from the "
                  "standard pet-fee fields because 'if required' does not "
                  "define the triggering condition. Preserve that exact "
                  "conditional charge wording in evidence/general notes.",
        "changes": "None -- the founder affirmed the proposal and directed that "
                   "the conditional charge wording be preserved.",
    }),
    ("woodspring suites cincinnati fairfield", {
        "founder_decision": "APPROVE_PUBLISH_STRUCTURED",
        "publishes": True,
        "ruling": "Approve pets_allowed true, dogs accepted, cats prohibited, "
                  "maximum 2 dogs per room, weight operator under/LT, "
                  "weight_limit 75 lbs per pet, $100 non-refundable pet "
                  "cleaning charge per pet as a SEPARATE charge, tier 1 "
                  "$25/night nights 1-6 scope unspecified, tier 2 $10 per pet "
                  "per night nights 7+. Do NOT invent 'per pet' scope for tier "
                  "1. Do NOT collapse the cleaning charge and nightly charges "
                  "into one headline fee.",
        "changes": "None -- the founder affirmed the proposal in full.",
    }),
))

#: Ruling #5 releases a fee Pass 3 withheld; ruling #6 releases a headline fee.
#: Everything else publishes exactly the facts Pass 3 proposed.
FOUNDER_FACT_OVERRIDES = {
    "hilton cincinnati netherland plaza": {
        "add": {"pet_fee": {"amount_cents": 5000, "currency": "USD",
                            "basis": "per_stay", "refundable_stated": False}},
        # ONLY the fee is released. The founder ruled "do not publish a
        # separate deposit", which is a decision to withhold it, not an
        # instruction to forget it: the deposit stays in withheld_fields with
        # SOURCE_CONTRADICTORY so the reason survives where a reader can find
        # it. Dropping the entry would make the page look simply silent about
        # a deposit it in fact names.
        "drop_withheld": ["pet_fee"],
    },
    "homewood suites by hilton cincinnati mason": {
        "add": {"pet_fee": {"amount_cents": 7500, "currency": "USD",
                            "basis": "per_stay", "refundable_stated": False}},
        "drop_withheld": ["pet_fee"],
    },
}

#: canonical_view reads the PLURAL keys. Pass 3 wrote plural already; this
#: guards a regression if a future capture writes the singular form.
_SPECIES_KEY = {"dog": "dogs", "cat": "cats", "dogs": "dogs", "cats": "cats"}


class ApplicationError(RuntimeError):
    pass


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _plural_species(facts: Dict) -> Dict:
    species = facts.get("species")
    if not isinstance(species, dict):
        return facts
    out = {}
    for name, state in species.items():
        key = _SPECIES_KEY.get(name)
        if key is None:
            raise ApplicationError("unknown species key %r" % name)
        out[key] = state
    facts = dict(facts)
    facts["species"] = out
    return facts


#: Canonical scope words. Pass 3 recorded "room" where the schema's enum is
#: "per_room"; a scope the validator rejects is a fact that never publishes.
_SCOPE = {"room": "per_room", "per_room": "per_room", "per_pet": "per_pet"}

#: The only wordings this corpus accepts as STATING a per-pet weight scope.
_PER_PET_RE = re.compile(r"per pet|any one (dog|pet)|each pet|per animal",
                         re.IGNORECASE)


def _money(cents, currency="USD"):
    return OrderedDict((("amount_cents", cents), ("currency", currency)))


def _tier(cents, lo, hi=None, role="REPLACEMENT_PRICE", basis_stated=False,
          basis=None, scope=None):
    """One fee tier in the shape the 1.3 validator actually requires.

    ``role`` is what separates a replacement price from an additional charge:
    without it "$100 pet fee + $200 cleaning" renders as a $100-$200 range.
    """
    t = OrderedDict((("amount_cents", cents), ("currency", "USD"),
                     ("role", role), ("condition_type", "stay_length_range"),
                     ("boundary_unit", "nights"), ("condition_min", lo),
                     ("basis_stated", basis_stated)))
    if hi is not None:
        t["condition_max"] = hi
    if basis:
        t["basis"] = basis
    if scope:
        t["scope"] = _SCOPE[scope]
    return t


def normalise(key, facts, quote=None, unstated_weight=None):
    """Pass 3's proposed facts -> schema 1.3, without changing what was read.

    Every transformation here is a SHAPE change. No value is added, removed or
    reinterpreted: the Red Roof rows keep the free first pet and the $105
    second-pet ceiling, they simply express it the way this market's four
    already-published Red Roof records express the identical policy.
    """
    f = dict(facts)
    if unstated_weight is None:
        unstated_weight = []

    # Red Roof: Pass 3 invented first_pet_fee / second_pet_fee_* fields. The
    # published Red Roof records carry the same policy as pet_fee + fee_cap
    # with the cap qualified to the SECOND pet, so a $105 ceiling is never
    # shown against a first pet that stays free.
    if "second_pet_fee_amount" in f or "first_pet_fee" in f:
        for dead in ("first_pet_fee", "second_pet_fee_amount",
                     "second_pet_fee_basis", "second_pet_fee_cap_amount",
                     "second_pet_fee_cap_basis", "second_pet_fee_cap_nights",
                     "weight_limit_lbs", "fee_tiers"):
            f.pop(dead, None)
        f["pet_fee"] = OrderedDict(_money(1500), basis="per_night",
                                   scope="per_pet")
        f["fee_cap"] = OrderedDict(
            list(_money(10500).items())
            + [("basis", "per_stay"), ("qualifier_stated", True),
               ("applies_to_pet_ordinal", 2), ("trigger_max_nights", 7)])
        # 80 lbs with no stated scope -- withheld on this market's own
        # precedent rather than published with a guessed scope.
        f.pop("weight_limit", None)

    if isinstance(f.get("pet_fee"), dict):
        fee = OrderedDict(f["pet_fee"])
        if "scope" in fee:
            fee["scope"] = _SCOPE[fee["scope"]]
        fee.setdefault("currency", "USD")
        f["pet_fee"] = fee

    if isinstance(f.get("fee_cap"), dict):
        cap = OrderedDict(f["fee_cap"])
        cap.setdefault("currency", "USD")
        if "scope" in cap:
            cap["scope"] = _SCOPE[cap["scope"]]
        cap.pop("qualifier_stated_text", None)
        # A qualifier the source SPELLS OUT is still a boolean here; the
        # words live in the quote, not in the flag.
        cap["qualifier_stated"] = bool(cap.pop("qualifier_stated", True))
        f["fee_cap"] = cap

    # weight_limit.scope is MANDATORY, and this market has always withheld the
    # limit rather than guess it -- see the four published Red Roof records,
    # whose withholding reason is that "Pet not to exceed 80 pounds" does not
    # disambiguate individual from combined. Hampton Airport North is why that
    # caution is not pedantry: it says "Total Combined Weight 50lbs", and a
    # guest with two 40lb dogs qualifies under a per-pet reading and does not
    # under the property's actual rule. So the scope is taken from the QUOTE,
    # never from a prior annotation, and an unstated scope withholds the field.
    if isinstance(f.get("weight_limit"), dict):
        w = OrderedDict(f["weight_limit"])
        stated = _PER_PET_RE.search(quote or "") is not None
        if stated:
            w["scope"] = "per_pet"
            f["weight_limit"] = w
        else:
            f.pop("weight_limit")
            unstated_weight.append(w.get("value"))

    if isinstance(f.get("combined_weight_limit"), dict):
        w = OrderedDict(f["combined_weight_limit"])
        w.pop("scope", None)
        f["combined_weight_limit"] = w

    # Tiers: rebuild every one into the canonical shape.
    tiers = f.get("fee_tiers")
    if tiers:
        rebuilt = []
        for t in tiers:
            if "pet_index" in t:          # Red Roof handled above; belt and braces
                continue
            if "nights_from" in t:
                rebuilt.append(_tier(t["amount_cents"], t["nights_from"],
                                     t.get("nights_to"),
                                     basis=t.get("basis"),
                                     scope=t.get("scope"),
                                     basis_stated=bool(t.get("basis"))))
            elif t.get("basis") == "per_week":
                # Ashley Quarters' weekly rate. There is no per_week basis in
                # the enum, so it is NOT forced into one: dropped from tiers
                # and reported, rather than published as something else.
                continue
        f["fee_tiers"] = rebuilt
        if not rebuilt:
            f.pop("fee_tiers")

    charges = f.get("other_charges")
    if charges:
        out = []
        for c in charges:
            ch = OrderedDict(list(_money(c["amount_cents"]).items()))
            ch["kind"] = {"cleaning": "cleaning_fee"}.get(c.get("kind"),
                                                          c.get("kind"))
            if c.get("scope"):
                ch["scope"] = _SCOPE[c["scope"]]
            ch["refundable_stated"] = True
            ch["refundable"] = False
            out.append(ch)
        f["other_charges"] = out

    return f

#: Genuine editorial withholdings ONLY. contracts.withholding is explicit that
#: withheld_fields means "we know something and are choosing not to publish
#: it", and that SOURCE_SILENT is INVALID inside it -- a page that simply never
#: mentions a weight limit produces ABSENCE, not a withholding entry. Pass 3
#: listed both kinds together; only these are real.
WITHHELD = {
    "hampton inn and suites cincinnati kenwood": {
        "species": ("SOURCE_AMBIGUOUS",
                    "The property's own policy string is truncated mid-word "
                    "('dog/cat onl'). The species are legible but sit inside "
                    "the cut-off clause; the founder ruled they must not be "
                    "completed from a sibling property's wording."),
        "pet_count_limit": ("SOURCE_AMBIGUOUS",
                            "Inside the same truncated clause."),
        "fee_tiers": ("SOURCE_AMBIGUOUS",
                      "Inside the same truncated clause. The $75 "
                      "non-refundable fee stated cleanly above it IS "
                      "published."),
    },
    "hilton cincinnati netherland plaza": {
        "deposit": ("SOURCE_CONTRADICTORY",
                    "The structured field calls the $50 a non-refundable FEE "
                    "and the prose beside it calls the same $50 a Non "
                    "Refundable Pet DEPOSIT. The founder ruled it a fee and "
                    "directed that no separate deposit be published; both "
                    "source strings are preserved in evidence."),
    },
    "days inn florence": {
        "other_charges": ("SOURCE_AMBIGUOUS",
                          "A 200 USD Pet Sanitation Fee is stated as applying "
                          "'if required', and the source never names the "
                          "condition that requires it. Publishing it as a "
                          "charge would tell a guest they always pay it."),
    },
    "woodspring suites cincinnati fairfield": {
        "pet_fee": ("SCHEMA_CANNOT_REPRESENT",
                    "The nightly rate DECLINES with stay length -- 25 USD for "
                    "the first 6 nights, then 10 USD per pet per night -- and "
                    "the two bands state different scopes. No single headline "
                    "pet_fee exists to publish; the tiers carry the schedule."),
    },
    "ashley quarters hotel cincinnati airport": {
        "fee_tiers": ("SCHEMA_CANNOT_REPRESENT",
                      "The property states a 90 USD WEEKLY rate alongside its "
                      "20 USD nightly rate. FEE_BASES has no per_week member, "
                      "so the weekly rate is withheld rather than converted "
                      "into a nightly or per-stay figure it is not."),
    },
}

#: Attached to every row whose stated weight limit had no stated scope.
_WEIGHT_SCOPE_WITHHOLDING = (
    "SOURCE_AMBIGUOUS",
    "The property states a maximum weight but never says whether it applies "
    "to each pet or to all pets combined. weight_limit requires a scope to "
    "publish, and this market has withheld it on exactly this ground before "
    "(the four published Red Roof records). Hampton Inn Cincinnati "
    "Airport-North is why: it states 'Total Combined Weight 50lbs', so the "
    "distinction changes who qualifies.")


def _evidence(row: Dict, fields: List[str]) -> List[Dict]:
    """One entry per published field, all citing the same captured artifact."""
    entries = []
    for field in fields:
        entry = OrderedDict((
            ("field", field),
            ("quote", row["quote"]),
            ("source_url", row["final_url"]),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", "sha256:%s" % row["sha256"]),
            ("artifact_kind", "rendered_html"),
            ("captured_at", OBSERVED_AT),
            ("capture_method", "attended_chrome_render"),
            ("source_grade", "PT1_FIRST_PARTY"),
        ))
        entry["evidence_ref"] = PM.evidence_ref_for(entry)
        entries.append(entry)
    return entries


def build_record(row: Dict, ruling: Dict = None) -> Dict:
    unstated_weight = []
    facts = normalise(row["identity_key"],
                      _plural_species(dict(row.get("facts") or {})),
                      quote=row.get("quote"), unstated_weight=unstated_weight)
    withheld = dict(WITHHELD.get(row["identity_key"], {}))
    if unstated_weight:
        withheld["weight_limit"] = _WEIGHT_SCOPE_WITHHOLDING

    override = FOUNDER_FACT_OVERRIDES.get(row["identity_key"])
    if override:
        facts.update(override["add"])
        for released in override["drop_withheld"]:
            withheld.pop(released, None)

    fields = [k for k in facts if k != "pets_allowed"]
    entries = _evidence(row, ["pets_allowed"] + fields)

    record = OrderedDict((
        ("key", row["identity_key"]),
        ("name", row.get("name") or row["identity_key"]),
        ("facts", facts),
        ("evidence", entries),
        ("evidence_count", len(entries)),
        ("evidence_quote", row["quote"]),
        ("source_url", row["final_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", OBSERVED_AT),
        ("verified_at", OBSERVED_AT),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", row["sha256"]),
        ("worker_routing_version", ""), ("worker_validator_version", ""),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("identity_key", row["identity_key"]),
        ("market_id", MARKET_ID),
    ))
    if row.get("service_animal_statement"):
        stmt = OrderedDict(row["service_animal_statement"])
        stmt.pop("classifier_note", None)
        record["service_animal_statement"] = stmt
    record["computation_class"] = classify(facts).computation_class
    if withheld:
        record["withheld_fields"] = OrderedDict(
            (field, OrderedDict((
                ("reason_code", code), ("reason", why),
                ("evidence_refs", [entries[0]["evidence_ref"]]))))
            for field, (code, why) in sorted(withheld.items()))

    caveats = [
        "%s. Founder block authorization of the 47 clean pet-friendly "
        "candidates from PTF-CINCINNATI-ZERO-COST-CAPTURE-003, applied against "
        "THIS record_hash." % WORK_ORDER,
        "Artifact evidence is a SHA256 computed live against the page's "
        "rendered outerHTML with the quote extracted from the same DOM in the "
        "same JavaScript call -- the convention this market's existing records "
        "already rest on. Attended browser only; provider calls 0, spend $0.00.",
    ]
    if ruling:
        caveats.insert(0, "FOUNDER EXCEPTION RULING (%s): %s"
                       % (ruling["founder_decision"], ruling["ruling"]))
        if ruling["changes"] != "None." and not \
                ruling["changes"].startswith("None"):
            caveats.append("Change from the disposition Pass 3 proposed: %s"
                           % ruling["changes"])
    record["approval"] = OrderedDict((
        ("decision", "APPROVED_AFTER_CURRENT_REVIEW"),
        ("operator", OPERATOR),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", PM.record_hash(record)),
        ("evidence_hash", PM.evidence_hash(entries)),
    ))
    return record


def build_exclusion(row: Dict) -> Dict:
    b = row.get("binding") or {}
    slug = "cin-" + row["identity_key"].replace(" ", "-")
    record = OrderedDict((
        ("exclusion_id", slug),
        ("canonical_name", row.get("name") or row["identity_key"]),
        ("normalized_name", row["identity_key"]),
        ("address", b.get("street") or ""),
        ("city", b.get("city") or ""),
        ("state", b.get("state") or ""),
        ("postal_code", b.get("postal_code") or ""),
        ("phone", ""),
        ("official_url", row["final_url"]),
        ("exclusion_state", "VERIFIED_NO_PETS"),
        ("evidence_quote", row["quote"]),
        ("source_url", row["final_url"]),
        ("observed_at", OBSERVED_AT),
        ("source_hash", "sha256:%s" % row["sha256"]),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", DECISION_DATE),
        ("notes", "%s: affirmative, property-specific refusal in the "
                  "property's own words, captured by attended browser at zero "
                  "cost. %s" % (WORK_ORDER, row.get("notes", ""))),
        ("market_id", MARKET_ID),
    ))
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def build():
    results = {r["identity_key"]: r for r in
               _load(REPORTS / "cincinnati_capture_pass3_001_results.json")["rows"]}
    clean_pf = _load(REPORTS / "cincinnati_capture_pass3_clean_pet_friendly.json")
    clean_np = _load(REPORTS / "cincinnati_capture_pass3_clean_verified_no_pets.json")

    if clean_pf["count"] != 47 or clean_np["count"] != 10:
        raise ApplicationError("clean block is not 47 + 10")

    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}

    new_records = [build_record(r) for r in clean_pf["rows"]]
    for key, ruling in RULINGS.items():
        if ruling["publishes"]:
            new_records.append(build_record(results[key], ruling))

    new_exclusions = [build_exclusion(r) for r in clean_np["rows"]]

    for rec in new_records:
        if rec["identity_key"] in published:
            raise ApplicationError("%s is already published" % rec["identity_key"])
    keys = [r["identity_key"] for r in new_records]
    if len(set(keys)) != len(keys):
        raise ApplicationError("duplicate identity in the applied set")
    ex_keys = [e["normalized_name"] for e in new_exclusions]
    if set(keys) & set(ex_keys):
        raise ApplicationError("an identity is both published and excluded")

    package["hotels"] = package["hotels"] + new_records
    problems = PM.validate_migrated(package)
    if problems:
        raise ApplicationError("package does not validate: %s" % problems[:8])

    return package, new_records, new_exclusions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        package, new_records, new_exclusions = build()
    except ApplicationError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("clean pet-friendly applied : 47")
    print("founder exceptions applied : %d of 8 (two publish nothing by ruling)"
          % sum(1 for r in RULINGS.values() if r["publishes"]))
    print("new policy records         : %d" % len(new_records))
    print("new exclusions             : %d" % len(new_exclusions))
    print("package total              : %d" % len(package["hotels"]))
    print("schema / contract issues   : %s / 0" % package["schema_version"])

    if args.write:
        decisions = OrderedDict((
            ("schema", "ptf-market-founder-decisions/1.0"),
            ("work_order", WORK_ORDER),
            ("parent_work_order", "PTF-CINCINNATI-ZERO-COST-CAPTURE-003"),
            ("market_id", MARKET_ID), ("as_of", DECISION_DATE),
            ("operator", OPERATOR),
            ("note", "The founder's eight exception rulings, verbatim, plus "
                     "the block authorization of the 57 clean candidates. "
                     "Recorded here as given; the application below derives "
                     "from them and never restates them."),
            ("block_authorization", OrderedDict((
                ("clean_pet_friendly", 47), ("clean_verified_no_pets", 10),
                ("verified_before_application", True),
                ("candidates_removed_from_block", 0),
            ))),
            ("count", len(RULINGS)),
            ("decision_counts", OrderedDict(sorted(Counter(
                r["founder_decision"] for r in RULINGS.values()).items()))),
            ("rows", [OrderedDict((("identity_key", k),) + tuple(v.items()))
                      for k, v in RULINGS.items()]),
        ))
        DECISIONS.write_text(json.dumps(decisions, indent=1,
                                        ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
        print("WROTE %s" % DECISIONS.name)

        PACKAGE.write_text(json.dumps(package, indent=1,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8", newline="\n")
        print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))

        path = MA.exclusions_shard_path(MARKET_ID)
        doc = MA.load_market_exclusions_document(MARKET_ID)
        shard = MA.build_exclusions_shard(
            MARKET_ID, list(doc["exclusions"]) + new_exclusions)
        path.write_text(MA.render_json(shard), encoding="utf-8", newline="")
        print("WROTE %s (%d exclusions)" % (path.name, shard["count"]))
    else:
        print("(check only -- pass --write)")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
