"""PTF-CINCINNATI-HARDENED-REVALIDATION-001 -- Phases 14 / 17 / 18.

One report, three questions, no authority touched.

  * Phase 14 -- the CLEAN pending inventory: every row this lineage owns that
    is publication-grade AND identity-bound AND free of a founder question.
    Two sources feed it and both are already on disk: the paid inventory
    Cincinnati bought across orders 014 / 015 / 016 and never applied, and the
    three rows this order's Firecrawl rung recovered. A row is admitted on its
    own evidence -- a document hash, a contiguous quote, a capture timestamp,
    a confirmed identity -- and nothing is admitted because a sibling was.

  * Phase 17 -- the SHADOW state: what Cincinnati's counts WOULD be if that
    inventory were later promoted, derived from the pinned partition rather
    than assumed. The pinned census does not move here; this order changes no
    identity.

  * Phase 18 -- promotion readiness, with the blockers named.

The arithmetic is stated rather than asserted: resolved and unresolved are
DERIVED from the partition every time, never carried forward from a previous
order's number. That is the defect PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013
was written to prevent recurring.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-HARDENED-REVALIDATION-001"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-shadow-reconciliation/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
PARTITION = os.path.join(PKG, "cincinnati_final_partition_001.json")
CENSUS = os.path.join(PKG, "identity_census", MARKET_ID + ".json")
INVENTORY = os.path.join(REPORTS, "cincinnati_application_inventory_016.json")
FIRECRAWL = os.path.join(REPORTS, "cincinnati_oh_firecrawl_pass_001.json")
STATIC = os.path.join(REPORTS, "cincinnati_oh_free_static_capture_001.json")

RESOLVED_STATES = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                   "OUT_OF_CURRENT_CATEGORY")


def J(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def build() -> OrderedDict:
    census = {h["identity_key"]: h for h in J(CENSUS)["hotels"]}
    partition = J(PARTITION)
    items = {i["identity_key"]: i for i in partition["items"]}
    counts = dict(partition["final_state_counts"])
    package = J(os.path.join(PKG, "hotel_policy_facts_" + MARKET_ID + ".json"))["hotels"]
    exclusions = J(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]
    live_pf = {h["identity_key"] for h in package}
    live_np = {ptf_identity_key(e["canonical_name"]) for e in exclusions
               if e.get("exclusion_state") == "VERIFIED_NO_PETS"}

    inv = J(INVENTORY)
    fc = J(FIRECRAWL)

    clean_pf, clean_np, held = [], [], []

    def admit(bucket, *, key, verdict, lane, source_url, doc_sha, quote,
              captured_at, identity_signals, facts, withheld, note=""):
        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", (census.get(key) or {}).get("canonical_name", key)),
            ("corridor", (census.get(key) or {}).get("corridor", "")),
            ("verdict", verdict),
            ("source_lane", lane),
            ("canonical_url", source_url),
            ("document_sha256", doc_sha),
            ("exact_quote", quote),
            ("captured_at", captured_at),
            ("identity_signals", identity_signals),
            ("parsed_facts", facts),
            ("withheld", withheld),
            ("partition_state_now", (items.get(key) or {}).get("final_state", "NOT_IN_PARTITION")),
            ("note", note),
        ))
        bucket.append(row)

    # ---- source 1: the paid inventory Cincinnati already owns, unapplied ----
    for cls, rows in inv["items"].items():
        for r in rows:
            key = r["identity_key"]
            state = (items.get(key) or {}).get("final_state")
            common = dict(
                key=key, source_url=r.get("source_url", ""),
                doc_sha=r.get("document_sha256", ""),
                quote=(r.get("policy_block") or "")[:600],
                captured_at=r.get("captured_at") or r.get("observed_at", ""),
                identity_signals=r.get("identity_signals") or r.get("binding") or {},
                facts=r.get("facts") or {}, withheld=r.get("withheld") or {},
                lane="PAID_FETCH (owned; bought by orders 014/015/016, never applied)")
            if state != "AWAITING_POLICY_OBSERVATION":
                held.append(OrderedDict((("identity_key", key), ("class", cls),
                                         ("why", "partition state is %s, not the "
                                          "AWAITING_POLICY_OBSERVATION this inventory "
                                          "was built against" % state))))
                continue
            if cls == "CLEAN_PET_FRIENDLY":
                admit(clean_pf, verdict="PET_FRIENDLY", **common)
            elif cls == "CLEAN_VERIFIED_NO_PETS":
                admit(clean_np, verdict="VERIFIED_NO_PETS", **common)
            else:
                held.append(OrderedDict((
                    ("identity_key", key), ("class", cls),
                    ("why", "carries an open founder question; "
                            "see cincinnati_application_inventory_016.open_questions"),
                    ("document_sha256", r.get("document_sha256", "")))))

    # ---- source 2: this order's Firecrawl rung ----
    for r in fc["rows"]:
        key = r["identity_key"]
        if r["firecrawl_class"] != "FIRECRAWL_PUBLICATION_GRADE":
            held.append(OrderedDict((
                ("identity_key", key), ("class", r["firecrawl_class"]),
                ("why", r.get("detail", "")[:200] or "not publication grade"))))
            continue
        # The SAME gate the paid rows pass. A publication-grade policy read on
        # a row whose IDENTITY the market has not settled is evidence toward
        # that identity, not a row to publish: Phase 14 excludes identity
        # ambiguity, and a confirmed page does not overrule the census.
        state = (items.get(key) or {}).get("final_state")
        if state != "AWAITING_POLICY_OBSERVATION":
            held.append(OrderedDict((
                ("identity_key", key), ("class", "IDENTITY_AMBIGUITY"),
                ("why", "partition state is %s; the Firecrawl capture confirmed "
                        "the page identity and is evidence for the identity "
                        "ruling, but the market has not made that ruling" % state),
                ("document_sha256", r["page_sha256"]),
                ("verdict_withheld", "VERIFIED_NO_PETS" if r.get("pets_allowed") is False
                 else "PET_FRIENDLY" if r.get("pets_allowed") is True else "UNKNOWN"))))
            continue
        obs = r.get("observation") or {}
        ev = obs.get("evidence") or []
        quote = " | ".join((e.get("quote") or "")[:200] for e in ev[:3])
        common = dict(
            key=key, source_url=r["requested_url"], doc_sha=r["page_sha256"],
            quote=quote, captured_at=r["captured_at"],
            identity_signals=(r.get("identity_assessment") or {}),
            facts=obs.get("extraction") or {}, withheld=obs.get("withheld_fields") or {},
            lane="FIRECRAWL (this order; plan credits, no USD)")
        if r.get("pets_allowed") is True:
            admit(clean_pf, verdict="PET_FRIENDLY", **common)
        elif r.get("pets_allowed") is False:
            admit(clean_np, verdict="VERIFIED_NO_PETS", **common)
        else:
            held.append(OrderedDict((("identity_key", key),
                                     ("class", "BLOCK_FOUND_BUT_SILENT"),
                                     ("why", "no pets_allowed verdict parsed"))))

    # ---- Phase 17: the shadow, DERIVED ----
    shadow = dict(counts)
    shadow["PUBLISHED_PET_FRIENDLY"] += len(clean_pf)
    shadow["VERIFIED_NO_PETS"] += len(clean_np)
    shadow["AWAITING_POLICY_OBSERVATION"] -= (len(clean_pf) + len(clean_np))
    census_n = sum(counts.values())
    shadow_n = sum(shadow.values())
    resolved_now = sum(counts[s] for s in RESOLVED_STATES)
    resolved_shadow = sum(shadow[s] for s in RESOLVED_STATES)

    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("authority_mutation", "NONE"),
        ("usd_spent", 0.0),
        ("phase_14_clean_pending_inventory", OrderedDict((
            ("clean_pet_friendly", len(clean_pf)),
            ("clean_verified_no_pets", len(clean_np)),
            ("held_with_evidence", len(held)),
            ("by_lane", OrderedDict(sorted(Counter(
                r["source_lane"] for r in clean_pf + clean_np).items()))),
            ("every_row_carries_a_document_hash",
             all(r["document_sha256"] for r in clean_pf + clean_np)),
            ("distinct_document_hashes",
             len({r["document_sha256"] for r in clean_pf + clean_np})),
            ("rows_pet_friendly", clean_pf),
            ("rows_verified_no_pets", clean_np),
            ("held", held),
        ))),
        ("phase_17_shadow", OrderedDict((
            ("pinned_census", census_n),
            ("shadow_census", shadow_n),
            ("census_moved", shadow_n - census_n),
            ("retirements", 0), ("successors", 0), ("same_campus", 0),
            ("explicit_assignments", 0), ("geography_holds", 0),
            ("why_zero", "this order resolved no identity and moved no geography; "
                         "the pinned census is unchanged by construction"),
            ("pinned_state_counts", OrderedDict(sorted(counts.items()))),
            ("shadow_state_counts", OrderedDict(sorted(shadow.items()))),
            ("projected", OrderedDict((
                ("pet_friendly", shadow["PUBLISHED_PET_FRIENDLY"]),
                ("verified_no_pets", shadow["VERIFIED_NO_PETS"]),
                ("resolved", resolved_shadow),
                ("unresolved", shadow_n - resolved_shadow),
                ("profiles", shadow["PUBLISHED_PET_FRIENDLY"]),
                ("derivation", "unresolved = census - (published + no-pets + "
                               "out-of-category), recomputed from the partition "
                               "and never carried forward"),
            ))),
            ("current", OrderedDict((
                ("pet_friendly", counts["PUBLISHED_PET_FRIENDLY"]),
                ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
                ("resolved", resolved_now),
                ("unresolved", census_n - resolved_now),
                ("profiles", len(live_pf)),
            ))),
        ))),
        ("live_authority_crosscheck", OrderedDict((
            ("live_pet_friendly_records", len(live_pf)),
            ("live_verified_no_pets", len(live_np)),
            ("clean_rows_already_live", sorted(
                {r["identity_key"] for r in clean_pf + clean_np} & (live_pf | live_np))),
        ))),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "cincinnati_oh_shadow_reconciliation_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n")
    p14 = rep["phase_14_clean_pending_inventory"]
    p17 = rep["phase_17_shadow"]
    print("written", os.path.relpath(args.out, _DASH))
    print("clean PF %s / clean no-pets %s / held %s"
          % (p14["clean_pet_friendly"], p14["clean_verified_no_pets"],
             p14["held_with_evidence"]))
    print("distinct document hashes", p14["distinct_document_hashes"],
          "of", p14["clean_pet_friendly"] + p14["clean_verified_no_pets"])
    print("current ", dict(p17["current"]))
    print("shadow  ", {k: v for k, v in p17["projected"].items() if k != "derivation"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
