# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-56-PROFILE-AUTHORITY-PROMOTION-017 -- the identity gate the builder does not have.

``market_proposed_authority_cli`` admits a signed row on three tests: it is in
the observation store, its founder decision publishes, and the record still
hashes to what was signed. All three are necessary. None of them asks the
question the membrane already answered -- IS THIS PAGE ABOUT THIS HOTEL.

So the builder will happily promote a row whose observation the identity gate
REJECTED, carrying facts the membrane refused, under a rule the codebase states
plainly:

    wrong property means no evidence, whatever the text says

This module closes that hole for Indianapolis and reports it as a gap in the
shared builder rather than pretending it is local.

WHAT ACTUALLY GETS REFUSED, AND WHY IT IS ONLY ONE
---------------------------------------------------
Indianapolis has five identities whose page name does not match the census
name. Four of them carry an identity ruling the FOUNDER gave in
PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003, and those rulings are already
baked into ``indianapolis_in_observation_store_003.json`` -- the store the
registered authority was projected from -- so the membrane returns VALID for
them and this gate never sees a rejection. That is the system working: a human
settled which building each one was, once, and the answer persisted.

The fifth, ``hampton inn indianapolis southwest plainfield``, has no such
ruling. Its census row says 2244 East Main Street and its page says 2244 East
Perry Road, so M10 refuses it and this gate refuses it too.

That refusal costs a profile, and the temptation is to write the fifth
override, because the evidence looks good: the census phone and the page phone
are the same ten digits and the page carries the Hilton property code the
sibling census row's URL also carries. The founder's own rule even admits "an
exact telephone" as sufficient.

It is still not mine to write. The overrides file records rulings A PERSON GAVE
about specific buildings; a ruling the founder did not give, transcribed by the
agent that needed it to reach a number, is not an approval -- it is the number
arranging its own evidence. The row is surfaced with its signals so the founder
can rule in one line, and the target is met without it either way.

The gate still consults the overrides on every rejection it sees, because a
future store may not have them applied and the escape has to exist where the
refusal happens.

NOTHING HERE PROMOTES OR PUBLISHES. This gates a proposal.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
WORK_ORDER = "PTF-INDIANAPOLIS-56-PROFILE-AUTHORITY-PROMOTION-017"
TARGET = 50

VALID = "VALID"


def load(name: str) -> Dict:
    return json.loads((LP / name).read_text(encoding="utf-8"))


def founder_identity_rulings() -> Dict[str, Dict]:
    doc = load("markets/founder_overrides/indianapolis-in.json")
    return {r["identity_key"]: r
            for r in doc["identity_overrides"]["records"]}


def gate(authority: Mapping, rulings: Mapping) -> Dict:
    """Split each authority bucket into admitted and refused."""
    admitted: Dict[str, List[Dict]] = {}
    refused: List[Dict] = []
    for bucket in ("pet_friendly", "verified_no_pets"):
        keep = []
        for row in authority[bucket]:
            key = row["normalized_name"]
            verdict = row.get("membrane_verdict", "")
            if verdict == VALID:
                keep.append(row)
                continue
            ruling = rulings.get(key)
            if ruling:
                keep.append(row)
                continue
            refused.append(OrderedDict((
                ("identity_key", key),
                ("canonical_name", row.get("canonical_name", "")),
                ("bucket", bucket),
                ("membrane_verdict", verdict),
                ("readiness_state", row.get("readiness_state", "")),
                ("why", "the identity membrane refused this observation and no "
                        "founder identity ruling covers it; wrong property "
                        "means no evidence, whatever the text says"),
            )))
        admitted[bucket] = keep
    return OrderedDict((("admitted", admitted), ("refused", refused)))


def duplicate_scans(rows: List[Dict]) -> Dict:
    """Three scans over the ADMITTED pet-friendly set, plus the two pairs this
    work order names by hand."""
    import re
    code = re.compile(r"/hotels/([a-z0-9]{5,8})-", re.I)

    def norm(url: str) -> str:
        return re.sub(r"^https?://(www\.)?", "",
                      (url or "").split("?")[0].rstrip("/").lower())

    by_url: Dict[str, List[str]] = {}
    by_code: Dict[str, List[str]] = {}
    by_key: Counter = Counter()
    for row in rows:
        key = row["normalized_name"]
        by_key[key] += 1
        url = norm(row.get("official_url") or row.get("source_url") or "")
        if url:
            by_url.setdefault(url, []).append(key)
        found = code.search(url)
        if found:
            by_code.setdefault(found.group(1).lower(), []).append(key)

    def collisions(mapping):
        return {k: v for k, v in mapping.items() if len(v) > 1}

    return OrderedDict((
        ("canonical_identity_duplicates",
         sorted(k for k, n in by_key.items() if n > 1)),
        ("canonical_url_duplicates", collisions(by_url)),
        ("brand_property_code_duplicates", collisions(by_code)),
        ("named_pairs_this_work_order_requires", OrderedDict((
            ("sw_vs_southwest_plainfield_hampton", OrderedDict((
                ("keys_in_authority",
                 sorted(k for k in by_key
                        if k in ("hampton inn indianapolis sw plainfield",
                                 "hampton inn indianapolis southwest plainfield"))),
                ("profiles_created",
                 sum(by_key[k] for k in
                     ("hampton inn indianapolis sw plainfield",
                      "hampton inn indianapolis southwest plainfield"))),
                ("requirement", "must not become two profiles"),
            ))),
            ("courtyard_springhill_601_w_washington", OrderedDict((
                ("courtyard_at_the_capitol_in_authority",
                 "courtyard by marriott indianapolis at the capitol" in by_key),
                ("springhill_downtown_in_authority",
                 "springhill suites indianapolis downtown" in by_key),
                ("requirement", "must remain TWO distinct hotels; neither is "
                                "signed, so this promotion neither merges nor "
                                "publishes them"),
            ))),
        ))),
    ))


def cross_market_collisions(keys) -> Dict:
    """Identity keys this market shares with ANOTHER market's authority.

    The within-market scans cannot see this, and it is the more dangerous
    direction: a bare brand name normalises the same everywhere. Indianapolis
    signed a row keyed ``home2 suites by hilton`` for the Carmel, IN property;
    Cleveland already routes that exact key to a Home2 Suites in Independence,
    OH. Two buildings, two states, one key.

    ``identity_routing`` fails closed on this ("the seed remains the source of
    truth"), so the collision would have surfaced as a contract failure rather
    than as bad data -- but only after the promotion was written. It belongs in
    the gate.
    """
    import csv
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

    routes = json.loads((LP / "identity_routing.json")
                        .read_text(encoding="utf-8")).get("routes") or ()
    elsewhere: Dict[str, List[str]] = {}
    for route in routes:
        if route.get("market_id") == "indianapolis-in":
            continue
        elsewhere.setdefault(
            route["hotel_ref"]["normalized_name"], []).append(route["market_id"])
    with (LP / "seed_businesses.csv").open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("market_id") == "indianapolis-in":
                continue
            name = (row.get("name") or "").strip()
            if name:
                elsewhere.setdefault(ptf_identity_key(name), []).append(
                    row["market_id"])

    found = []
    for key in sorted(keys):
        if key in elsewhere:
            found.append(OrderedDict((
                ("identity_key", key),
                ("also_claimed_by", sorted(set(elsewhere[key]))),
                ("why", "a bare brand name normalises identically in every "
                        "market; two buildings cannot share one identity key"),
            )))
    return OrderedDict((("collisions", found), ("count", len(found))))


def overlap_with_live(rows: List[Dict]) -> Dict:
    """A signed row is only a NEW profile if it is not already one."""
    live = {h["identity_key"] for h in
            load("hotel_policy_facts_indianapolis-in.json")["hotels"]}
    keys = {r["normalized_name"] for r in rows}
    return OrderedDict((
        ("live_before", len(live)),
        ("already_represented", sorted(keys & live)),
        ("absorbed_into_existing_identities", len(keys & live)),
        ("net_new_identities", len(keys - live)),
    ))


def build(authority_path: str) -> Dict:
    authority = json.loads(Path(authority_path).read_text(encoding="utf-8"))
    rulings = founder_identity_rulings()
    verdict = gate(authority, rulings)
    admitted = verdict["admitted"]
    pf, npets = admitted["pet_friendly"], admitted["verified_no_pets"]

    # A key another market already owns cannot be promoted here.
    cross = cross_market_collisions(r["normalized_name"] for r in pf)
    blocked = {c["identity_key"] for c in cross["collisions"]}
    for row in list(pf):
        if row["normalized_name"] in blocked:
            pf.remove(row)
            verdict["refused"].append(OrderedDict((
                ("identity_key", row["normalized_name"]),
                ("canonical_name", row.get("canonical_name", "")),
                ("bucket", "pet_friendly"),
                ("membrane_verdict", row.get("membrane_verdict", "")),
                ("readiness_state", row.get("readiness_state", "")),
                ("why", "this identity key is already claimed by another "
                        "market's authority; promoting it here would put two "
                        "buildings under one key"),
            )))

    overlap = overlap_with_live(pf)
    final_total = overlap["live_before"] + overlap["net_new_identities"]

    covered = [OrderedDict((
        ("identity_key", k),
        ("signals_agreeing", rulings[k].get("signals_agreeing")),
        ("ruled_in", rulings[k].get("work_order",
                    "PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003")),
    )) for k in sorted(rulings)
        if any(r["normalized_name"] == k and r.get("membrane_verdict") != VALID
               for b in ("pet_friendly", "verified_no_pets")
               for r in authority[b])]

    return OrderedDict((
        ("schema", "ptf-authority-promotion-gate/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("status", "SOURCE_PROMOTION_CANDIDATE"),
        ("nothing_is_published_by_this_file",
         "This gates a PROPOSAL. It assembles no bundle, issues no deployment "
         "authorisation, publishes no page and deploys nothing."),
        ("the_gap_this_module_closes", OrderedDict((
            ("builder", "scripts/pettripfinder/market_proposed_authority_cli.py"),
            ("what_it_checks", ["the row is in the observation store",
                                "the founder decision publishes",
                                "the record still hashes to what was signed"]),
            ("what_it_never_asks",
             "whether the identity membrane accepted the observation. It will "
             "promote a row the membrane marked REJECT_WRONG_PROPERTY, carrying "
             "facts read off a page that may be a different building."),
            ("severity", "this is a gap in a SHARED builder used by every "
                         "market, not an Indianapolis quirk; it deserves its "
                         "own hardening work order"),
            ("mitigation_here", "this module re-applies the membrane verdict "
                                "and admits a rejection only where a FOUNDER "
                                "identity ruling covers that exact row"),
        ))),
        ("identity_gate", OrderedDict((
            ("rule", "admit when membrane_verdict == VALID, or when a founder "
                     "identity ruling names this exact identity_key. Nothing "
                     "generalises: a ruling about one hotel never covers "
                     "another."),
            ("rejections_seen", len(verdict["refused"])
                                + len(covered)),
            ("admitted_on_a_founder_ruling", covered),
            ("refused", verdict["refused"]),
            ("refused_count", len(verdict["refused"])),
        ))),
        ("duplicate_scans", duplicate_scans(pf)),
        ("cross_market_identity_collisions", cross),
        ("counts", OrderedDict((
            ("signed_pet_friendly_evidence",
             len(authority["pet_friendly"])),
            ("admitted_pet_friendly", len(pf)),
            ("refused_on_identity",
             len(authority["pet_friendly"]) - len(pf)),
            ("live_promoted_before", overlap["live_before"]),
            ("absorbed_into_existing_identities",
             overlap["absorbed_into_existing_identities"]),
            ("net_new_distinct_identities", overlap["net_new_identities"]),
            ("final_distinct_pet_friendly", final_total),
            ("verified_no_pets", len(npets)),
            ("target", TARGET),
            ("target_met", final_total >= TARGET),
        ))),
        ("holds_and_exclusions", OrderedDict((
            ("identity_unresolved", [r["identity_key"]
                                     for r in verdict["refused"]]),
            ("founder_review_holds", sorted(
                {r["identity_key"] for name in
                 ("indianapolis_in_founder_signature_013.json",
                  "indianapolis_in_founder_signature_016.json")
                 for r in load(name).get("withheld") or ()})),
            ("unresolved_from_the_builder",
             list(authority.get("unresolved") or ())),
        ))),
        ("pet_friendly", pf),
        ("verified_no_pets", npets),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    doc = build(args.authority)
    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    counts = doc["counts"]
    print("signed pet-friendly evidence : %d" % counts["signed_pet_friendly_evidence"])
    print("refused on identity          : %d" % counts["refused_on_identity"])
    for row in doc["identity_gate"]["refused"]:
        print("   REFUSED %s (%s)" % (row["identity_key"], row["membrane_verdict"]))
    print("admitted pet-friendly        : %d" % counts["admitted_pet_friendly"])
    print("already live                 : %d" % counts["live_promoted_before"])
    print("absorbed into existing       : %d" % counts["absorbed_into_existing_identities"])
    print("net new distinct             : %d" % counts["net_new_distinct_identities"])
    print("FINAL DISTINCT PET-FRIENDLY  : %d (target %d, met=%s)"
          % (counts["final_distinct_pet_friendly"], TARGET, counts["target_met"]))
    print("verified-no-pets             : %d" % counts["verified_no_pets"])
    scans = doc["duplicate_scans"]
    print("duplicate scans              : identity=%s url=%s code=%s"
          % (scans["canonical_identity_duplicates"] or "clean",
             scans["canonical_url_duplicates"] or "clean",
             scans["brand_property_code_duplicates"] or "clean"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
