# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-FINAL-ZERO-COST-CLEANUP-018 -- six named items, no money.

Every item is settled from evidence already on disk. NO PROVIDER IS CALLED.

WHAT MOVED AND WHAT DELIBERATELY DID NOT
-----------------------------------------
Two rows become profiles, two names are corrected without becoming profiles,
one identity mismatch is repaired, and two things are handed back.

PLAINFIELD HAMPTON -- promoted. The membrane refused it because the census
says 2244 East Main Street and the page says 2244 East Perry Road. The
founder's own recorded rule admits "an exact telephone" as sufficient on its
own, and the census phone and the page phone are the same ten digits. 017
refused to write that ruling unasked; this work order asks for it by name, so
it is recorded here with the operator named as its author and the founder's
003 rule cited as the test applied.

OMNI SEVERIN -- promoted. 016 found that ``_ALLOWS`` had no "pet friendly"
pattern and left the one-line fix for its own work order rather than widening
a reading rule mid-review to raise its own count. This is that work order. The
pattern is added, eighteen controls hold, and the COMMITTED rules then approve
the block the locator already chose. No re-locate, no new evidence.

ESA AIRPORT W SOUTHERN AVE -- NOT promoted, handed back. Its capture does
contain a permission: "Pet Policy A maximum of two pets are allowed in each
suite." But it is not in the block the locator bounded, and that block is not
empty -- it states a fee schedule. 014's rule, written by this same corpus, is
that a HOLD on an EMPTY block may be re-located and a HOLD on an ASSERTING
block may not. Reaching this one needs a re-locate AND a founder fact override
to inject the permission. Both are the founder's, not mine. The quote and its
location are surfaced so the ruling takes one line.

HOME2 CARMEL -- name corrected, NOT promoted. The overlay fixes what a reader
sees and what the route slugifies from, and it was verified empirically that it
does NOT rekey the census identity. The identity key ``home2 suites by hilton``
still equals the key Cleveland routes to a hotel in Independence, Ohio, and
promoting a row on a key another market owns is the thing 017 refused. A census
rekey is the real fix and has its own authorisation.

TRU -- name corrected, already a profile. "Tru" publishes a directory entry
naming no building; the page says "Tru by Hilton Indianapolis Downtown".

THE 14 IDENTITY MISMATCHES -- one repaired, and no profiles recovered by any
of them. A refused capture persisted NO artifact, so there is nothing to read:
repair here means the identity rule stops refusing a page wrongly, not that a
policy came back. The one repair is a split directional -- "8520 N.W. Blvd."
against "8520 Northwest Boulevard" -- and sixteen controls confirm the other
thirteen stay disagreements.
"""
from __future__ import annotations

import argparse
import io
import json
import re
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from scripts.pettripfinder import indianapolis_founder_review_013 as R
from scripts.pettripfinder.brightdata.policy_surface import streets_agree
from scripts.pettripfinder.contracts import enums

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
WORK_ORDER = "PTF-INDIANAPOLIS-FINAL-ZERO-COST-CLEANUP-018"
REVIEWER = "PTF-FOUNDER-001"

PLAINFIELD = "hampton inn indianapolis southwest plainfield"
OMNI = "omni severin hotel indianapolis"
ESA = "extended stay america indianapolis airport w southern ave"


def load(name: str, enc: str = "utf-8") -> Dict:
    return json.loads((LP / name).read_text(encoding=enc))


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


# --------------------------------------------------------------------------
# item 1 -- the Plainfield Hampton identity ruling
# --------------------------------------------------------------------------

def plainfield_ruling() -> Dict:
    """Test the row against the founder's OWN recorded identity rule."""
    store = {r["identity_key"]: r
             for r in load("indianapolis_in_observation_store_017.json")["records"]}
    census = {h["identity_key"]: h
              for h in load("identity_census/indianapolis-in.json")["hotels"]}
    overrides = load("markets/founder_overrides/indianapolis-in.json")
    rule = overrides["identity_overrides"]["founder_ruling"]

    row, hotel = store[PLAINFIELD], census[PLAINFIELD]
    check = row["observation"]["identity_check"]
    phone_agrees = (_digits(hotel.get("phone"))
                    and _digits(hotel["phone"]) == _digits(check["phone_on_page"])[-10:])
    code = (check.get("property_code") or "").lower()
    code_on_url = code and code in (row["observation"]["source_url"] or "").lower()
    street_agrees, street_why = streets_agree(check.get("address_on_page", ""),
                                              hotel.get("address", ""))
    signals = OrderedDict((
        ("exact_telephone", OrderedDict((
            ("census", hotel.get("phone")), ("page", check.get("phone_on_page")),
            ("agrees", bool(phone_agrees))))),
        ("brand_property_code", OrderedDict((
            ("page", code), ("carried_by_the_url", bool(code_on_url)),
            ("agrees", bool(code and code_on_url))))),
        ("street_identity", OrderedDict((
            ("census", hotel.get("address")), ("page", check.get("address_on_page")),
            ("agrees", bool(street_agrees)), ("why", street_why)))),
    ))
    agreeing = [k for k, v in signals.items() if v["agrees"]]
    # The founder's rule: an exact telephone is sufficient ON ITS OWN.
    satisfied = bool(phone_agrees)
    return OrderedDict((
        ("identity_key", PLAINFIELD),
        ("canonical_name", row.get("canonical_name") or hotel["canonical_name"]),
        ("census_name", hotel["canonical_name"]),
        ("page_name", check.get("name_on_page")),
        ("founder_rule_applied", rule),
        ("signals", signals),
        ("signals_agreeing", agreeing),
        ("rule_satisfied", satisfied),
        ("why", "the founder's rule admits 'an exact telephone' on its own, and "
                "the census phone and the page phone are the same ten digits; "
                "the brand property code agrees as a second, independent signal"
                if satisfied else "no sufficient signal agrees"),
        ("street_disagreement_is_not_reconciled",
         "the census address and the page address name different streets and "
         "this ruling does NOT decide which is right. It says the phone "
         "identifies the building; correcting the census address is a separate "
         "question."),
        ("decided_by", "the operator, in %s, which names this row as an item "
                       "to work and directs promotion if it validates cleanly. "
                       "The TEST applied is the founder's own rule recorded in "
                       "PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003; this "
                       "file records the application, not a new rule."
                       % WORK_ORDER),
    ))


# --------------------------------------------------------------------------
# item 6 -- routing repair over the 14, deterministic only
# --------------------------------------------------------------------------

def routing_repair() -> Dict:
    run = load("indianapolis_in_market_acquisition_012.json")
    census = {h["identity_key"]: h
              for h in load("identity_census/indianapolis-in.json")["hotels"]}
    rows: List[Dict] = []
    for result in run["results"]:
        if result["outcome"] != "IDENTITY_MISMATCH":
            continue
        key = result["identity_key"]
        detail = result.get("detail") or ""
        hotel = census.get(key, {})
        street = re.search(r"page street '([^']+)' does not agree with "
                           r"expected '([^']+)'", detail)
        name = re.search(r"page names '([^']+)', which does not agree with "
                         r"'([^']+)'", detail)
        agrees, why = (streets_agree(street.group(1), street.group(2))
                       if street else (False, ""))
        rows.append(OrderedDict((
            ("identity_key", key),
            ("kind", "STREET" if street else "NAME"),
            ("census_address", hotel.get("address")),
            ("page_address", street.group(1) if street else None),
            ("page_name", name.group(1) if name else None),
            ("repaired", bool(agrees)),
            ("repair_rule", why),
            ("still_unresolved_because",
             "" if agrees else
             ("the page names a different street or house number, which is a "
              "different building and not a notation difference"
              if street else
              "the page states a marketing or directory name that no "
              "deterministic rule maps to this identity; a person must say "
              "whether it is the same hotel")),
            ("policy_recovered", False),
            ("saved_artifact", bool(result.get("artifact_dir"))),
        )))
    repaired = [r for r in rows if r["repaired"]]
    return OrderedDict((
        ("examined", len(rows)),
        ("repaired", len(repaired)),
        ("still_unresolved", len(rows) - len(repaired)),
        ("repaired_keys", [r["identity_key"] for r in repaired]),
        ("no_policy_was_recovered",
         "A refused capture persisted no artifact -- 0 of the 14 kept a page. "
         "Repair here means the identity rule stops refusing a page wrongly; "
         "it does not recover a policy, and no row became a profile."),
        ("by_kind", OrderedDict(sorted(Counter(r["kind"] for r in rows).items()))),
        ("rows", rows),
    ))


# --------------------------------------------------------------------------
# items 4 and 5 -- the two reader/evidence HOLDs
# --------------------------------------------------------------------------

def omni_resolution() -> Dict:
    """016's held row, re-ruled by the COMMITTED rules after the reader fix."""
    run = load("indianapolis_in_market_acquisition_016.json")
    result = next(r for r in run["results"] if r["identity_key"] == OMNI)
    block = R._block(result.get("artifact_dir", ""))
    reading = R.read_block(block)
    disposition, reason = R.rule({"policy_block": block}, reading)
    return OrderedDict((
        ("identity_key", OMNI),
        ("canonical_name", result.get("canonical_name", "")),
        ("what_changed", "_ALLOWS gained an anchored 'is/are a pet friendly' "
                         "pattern. Nothing else moved: the block is the one the "
                         "locator already bounded, and no evidence was "
                         "re-located or re-acquired."),
        ("policy_block", block),
        ("reading", reading),
        ("disposition", disposition),
        ("reason", reason),
        ("semantic_hash", R._semantic_hash(
            {"identity_key": OMNI, "policy_block": block,
             "source_url": result.get("source_url", "")})),
        ("content_hash", result.get("content_hash", "")),
        ("source_url", result.get("source_url", "")),
        ("completed_at", result.get("completed_at", "")),
        ("promotable", disposition == R.APPROVE_PET_FRIENDLY),
    ))


def esa_handback() -> Dict:
    """Item 5. The permission exists; reaching it is the founder's call."""
    run = load("indianapolis_in_market_acquisition_012.json")
    result = next(r for r in run["results"] if r["identity_key"] == ESA)
    artifact = (result.get("artifact_dir") or "").replace(chr(92), "/")
    block = R._block(result.get("artifact_dir", ""))
    text = io.open(artifact + "/page-text.txt", encoding="utf-8",
                   errors="replace").read()
    html = io.open(artifact + "/rendered.html", encoding="utf-8",
                   errors="replace").read()
    # Whitespace-tolerant: the captured text wraps between "Pet Policy" and
    # the sentence, and matching the pretty-printed form finds nothing.
    quote = re.search(r"Pet\s+Policy\s+A\s+maximum\s+of\s+two\s+pets\s+are\s+"
                      r"allowed\s+in\s+each\s+suite\.", text)
    refusals = [p for p in (r"pets?\s+(are\s+)?not\s+allowed", r"no\s+pets\s+allowed",
                            r"pets\s+allowed\s*:\s*no", r"\bno\s+pets\b",
                            r'"petsAllowed"\s*:\s*false')
                if re.search(p, html, re.I) or re.search(p, text, re.I)]
    return OrderedDict((
        ("identity_key", ESA),
        ("canonical_name", result.get("canonical_name", "")),
        ("state", "STILL HELD -- handed back to the founder"),
        ("the_permission_is_in_the_capture", bool(quote)),
        ("quote", quote.group(0) if quote else ""),
        ("quote_location", "page-text.txt, under the heading 'Pet Policy'"),
        ("committed_rules_would_approve_that_sentence",
         R.rule({"policy_block": quote.group(0) if quote else ""},
                R.read_block(quote.group(0) if quote else ""))[0]),
        ("contradicting_refusals_in_the_whole_capture", refusals or "none"),
        ("held_block", block),
        ("why_it_is_not_resolved_here", OrderedDict((
            ("the_block_asserts_something",
             "unlike the Home2 block that 014 re-located off, this block is not "
             "empty: it states a full fee schedule. 014's own rule is that a "
             "HOLD on an EMPTY block is re-locatable and a HOLD on an ASSERTING "
             "block is not."),
            ("two_founder_acts_would_be_needed",
             "a re-locate off an asserting block, and a fact override to inject "
             "pets_allowed into the observation. Both belong to the founder."),
            ("what_is_NOT_in_doubt",
             "the capture contains no refusal anywhere, and the block's fee "
             "schedule agrees with the page's; the $250 figures are a smoking "
             "fee and an incidental deposit, not a second pet-fee basis."),
        ))),
        ("what_a_ruling_would_need_to_say",
         "that the quoted sentence may be read as this property's pet "
         "permission, and that its fee schedule publishes as stated"),
    ))


# --------------------------------------------------------------------------
# the document
# --------------------------------------------------------------------------

def name_corrections() -> Dict:
    doc = load("markets/name_corrections/indianapolis-in.json")
    package = {h["identity_key"] for h in
               load("hotel_policy_facts_indianapolis-in.json")["hotels"]}
    rows = []
    for record in doc["records"]:
        key = record["identity_key"]
        rows.append(OrderedDict((
            ("identity_key", key),
            ("census_name", record["census_canonical_name"]),
            ("corrected_name", record["corrected_canonical_name"]),
            ("cited_to", record["source_url"]),
            ("already_a_profile", key in package),
            ("rekeys_the_identity", False),
            ("effect", "the published name and the route slug change; the "
                       "census identity key does not"),
        )))
    return OrderedDict((("count", len(rows)), ("records", rows)))


def build() -> Dict:
    plainfield = plainfield_ruling()
    omni = omni_resolution()
    esa = esa_handback()
    routing = routing_repair()
    names = name_corrections()

    # What the market held when THIS work order started. A constant, not a
    # read of the live package: 018 promotes into that package, so
    # recomputing the start from it after the fact reports "56 -> 58" and
    # counts this run's own gain twice. 016 and 014 both had to be pinned
    # the same way.
    start = 54
    gained = [k for k, ok in ((PLAINFIELD, plainfield["rule_satisfied"]),
                              (OMNI, omni["promotable"])) if ok]

    return OrderedDict((
        ("schema", "ptf-market-cleanup/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("nothing_was_fetched", True),
        ("nothing_is_published_by_this_file",
         "This settles six named items from evidence already on disk. It "
         "assembles no bundle, issues no deployment authorisation, publishes "
         "no page and deploys nothing."),
        ("item_1_plainfield_hampton_identity_ruling", plainfield),
        ("item_2_and_3_canonical_name_corrections", names),
        ("item_4_omni_severin", omni),
        ("item_5_esa_fee_only_hold", esa),
        ("item_6_routing_repair", routing),
        ("home2_is_still_refused", OrderedDict((
            ("identity_key", "home2 suites by hilton"),
            ("name_corrected", True),
            ("promoted", False),
            ("why", "the overlay corrects the NAME and was verified not to "
                    "rekey the census identity. The key still equals the one "
                    "Cleveland routes to a hotel in Independence, OH, and "
                    "promoting a row on a key another market owns is what 017 "
                    "refused. A census rekey is the fix and needs its own "
                    "authorisation."),
        ))),
        ("counts", OrderedDict((
            ("starting_pet_friendly", start),
            ("newly_promotable", sorted(gained)),
            ("ending_pet_friendly", start + len(gained)),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    doc = build()
    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    p = doc["item_1_plainfield_hampton_identity_ruling"]
    print("1 plainfield   : rule_satisfied=%s signals=%s"
          % (p["rule_satisfied"], p["signals_agreeing"]))
    n = doc["item_2_and_3_canonical_name_corrections"]
    for r in n["records"]:
        print("2/3 name       : %-24s -> %r (profile=%s)"
              % (r["identity_key"], r["corrected_name"], r["already_a_profile"]))
    print("4 omni         : %s" % doc["item_4_omni_severin"]["disposition"])
    print("5 esa          : %s" % doc["item_5_esa_fee_only_hold"]["state"])
    r = doc["item_6_routing_repair"]
    print("6 routing      : examined %d, repaired %d, unresolved %d, policies recovered 0"
          % (r["examined"], r["repaired"], r["still_unresolved"]))
    c = doc["counts"]
    print("pet-friendly   : %d -> %d  %s"
          % (c["starting_pet_friendly"], c["ending_pet_friendly"],
             c["newly_promotable"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
