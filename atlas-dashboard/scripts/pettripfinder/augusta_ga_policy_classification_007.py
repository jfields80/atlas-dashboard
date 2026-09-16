"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 16-19: negation-safe
policy classification and final one-disposition-per-property accounting.

Every one of the market's admitted census identities gets EXACTLY one
disposition. Safety rules actually enforced here (not just stated):

1. A generic "pet friendly" amenity chip alone never publishes acceptance.
2. Explicit refusal wording safety-checks against a naive parser: this order
   found TWO large blocks of Wyndham page text -- "Dogs Welcome... Pet-
   Friendly... Pet-friendly hotel by Fort Eisenhower and Augusta National
   Golf Club" and "ADA defined service animals are welcome... Sorry no other
   pets are allowed" -- BYTE-IDENTICAL (down to a shared mis-rendered "�"
   character) across many DIFFERENT real properties at different real
   addresses, every one of them with identity_confirmed_on_page = False.
   That is the signature of a shared area/template content block, not a
   property-specific statement, and it is safety-checked out here rather
   than trusted: every row whose ONLY captured text is one of these two
   blocks is held (EVIDENCE_HOLD for the positive block, NEGATION_HOLD for
   the service-animal-only block), never published either direction.
3. Service-animal-only language is NEVER read as verified no-pets on its
   own steam (Phase 17) -- it is a NEGATION_HOLD unless a second, genuinely
   property-specific signal corroborates it (a distinct fee/count/weight
   number that does not appear on any other property's capture).
4. Only explicitly supported facts are recorded; UNKNOWN stays UNKNOWN.

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_final_partition_007.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
PLAN = os.path.join(PKG, "markets", "reports", "augusta_ga_acquisition_cost_plan_003.json")
STATIC = os.path.join(PKG, "markets", "reports", "augusta_ga_static_lane_001.json")
FIRECRAWL = os.path.join(PKG, "markets", "reports", "augusta_ga_firecrawl_acquisition_005.json")
ATTENDED = os.path.join(PKG, "markets", "reports", "augusta_ga_attended_capture_006.json")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_final_partition_007.json")

# The two shared/template text blocks this order caught and refuses to trust
# as property-specific (see module docstring). Matched by a short, stable
# substring of each.
SHARED_POSITIVE_BOILERPLATE = "pet-friendly hotel by fort eisenhower and augusta national golf club"
SHARED_NEGATIVE_BOILERPLATE = "sorry no other pets are allowed"

EXPLICIT_NO = ("pets not allowed", "pets allowed: no", "not allowed at this location",
               "does not allow pets", "no, pets are not allowed")
EXPLICIT_YES_STRUCTURED = ("pets allowed: yes", "pets welcome", "dogs welcome")

# Independently re-verified via the live wyndhamhotels.com search-results
# modal (its own "Hotel Policies" panel, opened directly from this
# property's own card) -- confirms the Firecrawl capture text genuinely
# belongs to THIS property and is not the generic search-hub content every
# other Wyndham-family row in this cohort landed on (the /overview URL
# shape redirects to a shared city+brand search hub for every property in
# the family -- a real routing defect, documented in this module's
# docstring). This is the one row this order can promote out of the
# shared-boilerplate hold with real confidence; no other row in that cohort
# has been independently confirmed this way.
INDEPENDENTLY_VERIFIED_NO_PETS = {
    "wingate by wyndham augusta washington road": {
        "operative_quote": "PET POLICY: ADA defined service animals are welcome. Sorry no other pets are "
                            "allowed. Any unauthorized pets found in guestrooms a 250.00USD pet fee will be "
                            "accessed.",
        "parsed_facts": {"acceptance": "NOT_ALLOWED", "service_animal_exception": True, "unauthorized_pet_fee": 250.0},
    },
}


def classify_firecrawl_row(identity_key, row):
    sentences = [s.lower() for s in (row.get("pet_sentences") or [])]
    joined = " | ".join(sentences)
    if not sentences:
        return "SOURCE_SILENT", None, {}
    if SHARED_POSITIVE_BOILERPLATE in joined and not any(
            c.isdigit() for s in sentences if SHARED_POSITIVE_BOILERPLATE not in s for c in s):
        # every sentence is either the shared block or carries no distinguishing number
        return "EVIDENCE_HOLD", ("shared area-boilerplate text also found verbatim on other "
                                  "properties; identity_confirmed_on_page was False; held rather "
                                  "than published as this property's own statement"), {}
    if SHARED_NEGATIVE_BOILERPLATE in joined:
        # An explicit "no other pets are allowed" is the dominant signal no
        # matter what else co-occurs with it -- including a same-row "$250
        # unauthorized pet fee" penalty number, which REINFORCES a no-pets
        # reading rather than overriding it (a first version of this
        # classifier let that digit fall through to the positive-fact
        # branch below and wrongly published Wingate Washington Road as
        # CLEAN_PET_FRIENDLY; fixed here). It is still only a HOLD, never a
        # published no-pets, because Phase 17 forbids inferring verified
        # no-pets from service-animal-only language on its own, and this
        # text is byte-identical shared boilerplate on other properties too
        # (identity_confirmed_on_page False on every row that carries it).
        return "NEGATION_HOLD", ("service-animal-only refusal wording found (byte-identical shared "
                                  "area-boilerplate on other properties, identity_confirmed_on_page "
                                  "False); Phase 17 forbids inferring verified no-pets from "
                                  "service-animal-only language alone, so this is held either way, "
                                  "never published as pet-friendly even when a same-row penalty "
                                  "fee number is present"), {}
    for phrase in EXPLICIT_NO:
        if phrase in joined:
            return "CLEAN_VERIFIED_NO_PETS", row.get("pet_sentences"), {"acceptance": "NOT_ALLOWED"}
    # a real, property-specific number OUTSIDE either shared-boilerplate block,
    # in a sentence that is actually about pets/fees/weight/count -- this is
    # what distinguishes Staybridge's "$75...$150...30lbs" or Red Roof's
    # "$15/night...80 pounds" from the two generic templated blocks, which
    # never carry property-specific digits at all.
    fact_markers = ("fee", "lbs", "pound", "night", "stay", "deposit", "charge", "weigh", "pet")
    for s in sentences:
        if SHARED_POSITIVE_BOILERPLATE in s or SHARED_NEGATIVE_BOILERPLATE in s:
            continue
        if any(ch.isdigit() for ch in s) and any(m in s for m in fact_markers):
            return "CLEAN_PET_FRIENDLY", row.get("pet_sentences"), {"acceptance": "ALLOWED", "note": "fee/count/weight in operative_quote, not further parsed here"}
    if any(p in joined for p in EXPLICIT_YES_STRUCTURED):
        return "CLEAN_PET_FRIENDLY", row.get("pet_sentences"), {"acceptance": "ALLOWED", "note": "explicit acceptance wording, no further fee/count/weight found"}
    return "EVIDENCE_HOLD", ("pet-related text found but neither an explicit refusal nor a "
                              "property-differentiated acceptance with a real number"), {}


def main():
    census = json.load(open(CENSUS, encoding="utf-8"))
    hotels = {h["identity_key"]: h for h in census["hotels"]}
    plan = json.load(open(PLAN, encoding="utf-8"))
    lane_of = {d["identity_key"]: d for d in plan["decisions"]}
    static = json.load(open(STATIC, encoding="utf-8"))
    static_by_key = {}
    for r in static.get("rows", []):
        for k in r.get("census_identity_keys", []):
            static_by_key.setdefault(k, []).append(r)
    firecrawl = json.load(open(FIRECRAWL, encoding="utf-8"))
    fc_by_key = {r["identity_key"]: r for r in firecrawl.get("rows", [])}
    attended = json.load(open(ATTENDED, encoding="utf-8"))
    at_by_key = {r["identity_key"]: r for r in attended.get("rows", [])}

    partition = []
    for key, h in hotels.items():
        disp = OrderedDict([("identity_key", key), ("canonical_name", h.get("canonical_name")),
                            ("corridor", h.get("corridor")), ("postal_code", h.get("postal_code"))])
        d = lane_of.get(key)

        if key in at_by_key:
            row = at_by_key[key]
            sc = row.get("source_class")
            facts = row.get("parsed_facts") or {}
            if sc == "ATTENDED_PUBLICATION_GRADE" and facts.get("acceptance") == "ALLOWED":
                disp["disposition"] = "CLEAN_PET_FRIENDLY"
            elif sc == "ATTENDED_PUBLICATION_GRADE" and facts.get("acceptance") == "NOT_ALLOWED":
                disp["disposition"] = "CLEAN_VERIFIED_NO_PETS"
            elif sc == "ACCESS_BLOCKED":
                disp["disposition"] = "ACCESS_BLOCKED"
                disp["access_blocked_accounting"] = OrderedDict([
                    ("static_attempt", "N/A -- no non-Hilton first-party URL"),
                    ("official_route", row.get("requested_url")),
                    ("firecrawl_eligible", False),
                    ("firecrawl_attempt", "NOT_ATTEMPTED -- Hilton is a measured KNOWN_CAPABILITY_WALL, never a candidate"),
                    ("firecrawl_result", "N/A"), ("other_provider_fallback", "NONE_AUTHORIZED"),
                    ("supported_browser_result", "BLOCKED -- Hilton's own error page after the first few reads this session"),
                    ("final_block_reason", row.get("block_reason")),
                ])
            else:
                disp["disposition"] = "SOURCE_SILENT"
            disp["operative_quote"] = row.get("operative_quote")
            disp["parsed_facts"] = facts
            disp["evidence_lane"] = "ATTENDED_BROWSER"
            partition.append(disp)
            continue

        if key in INDEPENDENTLY_VERIFIED_NO_PETS:
            v = INDEPENDENTLY_VERIFIED_NO_PETS[key]
            disp["disposition"] = "CLEAN_VERIFIED_NO_PETS"
            disp["operative_quote"] = v["operative_quote"]
            disp["parsed_facts"] = v["parsed_facts"]
            disp["evidence_lane"] = "FIRECRAWL_INDEPENDENTLY_VERIFIED"
            partition.append(disp)
            continue

        family = (d or {}).get("family")
        is_unstable_wyndham_hub = (family == "WYNDHAM" and
                                    (family == "WYNDHAM" and
                                     ((d or {}).get("url") or "").rstrip("/").endswith("overview")))

        if key in fc_by_key:
            row = fc_by_key[key]
            if is_unstable_wyndham_hub:
                # PROPERTY_SPECIFIC_HUB_LEAK_NOTE: the wyndhamhotels.com
                # "/overview" URL shape 302s to a generic city+brand search
                # hub for every property in the family (confirmed via a real
                # browser session, not just Firecrawl). Worse, the hub's
                # rendered content is NON-DETERMINISTIC across fetches --
                # re-fetching the IDENTICAL URL for "days inn by wyndham
                # thomson" and "super 8 augusta ga" returned different pet
                # text on a later call than the first, after this order had
                # already trusted the first fetch's specific numbers. No
                # Wyndham-family capture through this URL shape is trusted,
                # regardless of what text it happens to contain on any one
                # fetch, except the one row independently re-verified through
                # a different capture path (INDEPENDENTLY_VERIFIED_NO_PETS
                # above). IHG and Choice brand URLs never showed this defect
                # (each fetch returned stable, property-differentiated
                # content) and are still classified normally below.
                disp["disposition"] = "EVIDENCE_HOLD"
                disp["operative_quote"] = row.get("pet_sentences")
                disp["parsed_facts"] = {}
                disp["note"] = ("Wyndham /overview URL is a confirmed non-deterministic shared search-hub "
                                 "redirect, not a stable property page; held regardless of captured text "
                                 "(see PROPERTY_SPECIFIC_HUB_LEAK_NOTE)")
            else:
                outcome, quote, facts = classify_firecrawl_row(key, row)
                disp["disposition"] = outcome
                disp["operative_quote"] = quote
                disp["parsed_facts"] = facts
            disp["evidence_lane"] = "FIRECRAWL"
            disp["requested_url"] = row.get("requested_url")
            partition.append(disp)
            continue

        srows = static_by_key.get(key, [])
        svalid = [r for r in srows if r.get("outcome") == "VALID"]
        if svalid:
            r = svalid[0]
            joined = " | ".join(s.lower() for s in (r.get("pet_sentences") or []))
            if is_unstable_wyndham_hub:
                disp["disposition"] = "EVIDENCE_HOLD"
                disp["note"] = ("Wyndham /overview URL is a confirmed non-deterministic shared search-hub "
                                 "redirect (see PROPERTY_SPECIFIC_HUB_LEAK_NOTE); held regardless of captured text")
            elif any(p in joined for p in EXPLICIT_NO):
                disp["disposition"] = "CLEAN_VERIFIED_NO_PETS"
            elif any(ch.isdigit() for ch in joined) and "pet" in joined:
                disp["disposition"] = "CLEAN_PET_FRIENDLY"
            else:
                disp["disposition"] = "EVIDENCE_HOLD"
            disp["operative_quote"] = r.get("pet_sentences")
            disp["evidence_lane"] = "DIRECT_STATIC_FETCH"
            partition.append(disp)
            continue

        if d is None:
            disp["disposition"] = "GEOGRAPHY_HOLD"
            disp["note"] = "not present in the acquisition cost plan (post-merge census row) -- needs a fresh plan pass"
        elif d["next_lane"] == "LOCAL_FREE_DISCOVERY":
            disp["disposition"] = "ROUTING_HOLD"
            disp["note"] = "no first-party URL found by any free lane (owned, brand inventory, competitor lead, WebSearch identity discovery); needs a paid identity-discovery lane or further manual research, not yet requested"
        elif d["next_lane"] == "DIRECT_STATIC_FETCH":
            disp["disposition"] = "EVIDENCE_HOLD"
            disp["note"] = "router assigned DIRECT_STATIC_FETCH but this row was not among the static lane's fetched targets in this pass"
        else:
            disp["disposition"] = "FOUNDER_REVIEW"
            disp["note"] = "unclassified by any lane this pass"
        partition.append(disp)

    tally = Counter(p["disposition"] for p in partition)
    assert sum(tally.values()) == len(hotels), "every hotel must get exactly one disposition"

    doc = OrderedDict([
        ("schema", "ptf-final-partition/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("census_count", len(hotels)), ("disposition_tally", dict(tally)),
        ("negation_safety_catches", {
            "evidence_hold_shared_positive_boilerplate": sum(
                1 for p in partition if p["disposition"] == "EVIDENCE_HOLD" and p.get("evidence_lane") == "FIRECRAWL"),
            "negation_hold_shared_service_animal_boilerplate": sum(
                1 for p in partition if p["disposition"] == "NEGATION_HOLD"),
        }),
        ("partition", partition),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("census_count", len(hotels), "tally", dict(tally))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
