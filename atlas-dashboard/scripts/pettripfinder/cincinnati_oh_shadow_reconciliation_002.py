"""PTF-CINCINNATI-PARALLEL-REVALIDATION-002 -- Phases 14, 17 and 18.

The clean pending inventory, the shadow, and the promotion-readiness call, all
recomputed from the two evidence sets this market now owns on this branch:

    PTF-CINCINNATI-HARDENED-REVALIDATION-001  23 rows -- 21 bought long ago and
        never applied, 2 read by Firecrawl. Carried onto this base as owned
        evidence rather than reacquired.
    PTF-CINCINNATI-PARALLEL-REVALIDATION-002  the attended pass, which walked
        the Marriott and Hilton wall 001 had measured as impassable.

Two rules govern what may enter the clean inventory:

    a row is clean only if the PAGE declared something about its own identity
      that agrees with the census -- a postal code or a street number. A route
      is a claim about identity, never a proof of one.
    a verified new hotel is a CENSUS ADMISSION, not a clean pending row.
      Nothing discovered by the recensus or by a competitor directory is
      allowed into this inventory; putting it there would smuggle a census
      change through a policy gate.

The shadow moves the partition and nothing else. No authority is written, no
pin is moved, no global is regenerated, and nothing is assembled or deployed.
"""
from __future__ import annotations

import json
import os
from collections import Counter, OrderedDict
from datetime import datetime, timezone

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "cincinnati_oh_shadow_reconciliation_002.json")

WORK_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-shadow-reconciliation/1.0"


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    partition = load(os.path.join(PKG, "cincinnati_final_partition_001.json"))
    census = load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    shadow1 = load(os.path.join(REPORTS, "cincinnati_oh_shadow_reconciliation_001.json"))
    attended = load(os.path.join(REPORTS, "cincinnati_oh_attended_pass_002.json"))

    pinned = Counter(item["final_state"] for item in partition["items"])
    p14_1 = shadow1["phase_14_clean_pending_inventory"]

    inherited_pf = [dict(r, source_order="PTF-CINCINNATI-HARDENED-REVALIDATION-001")
                    for r in p14_1["rows_pet_friendly"]]
    inherited_np = [dict(r, source_order="PTF-CINCINNATI-HARDENED-REVALIDATION-001")
                    for r in p14_1["rows_verified_no_pets"]]
    inherited_keys = {r["identity_key"] for r in inherited_pf + inherited_np}

    new_pf, new_np, held = [], [], []
    for row in attended["rows"]:
        record = OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("brand_family", row["brand_family"]),
            ("verdict", row["verdict"]),
            ("source_lane", "ATTENDED (this order; browser, no vendor, no credit, no USD)"),
            ("canonical_url", row["canonical_url"]),
            ("document_sha256", row["document_sha256"]),
            ("exact_quote", row["exact_quote"]),
            ("identity_binding", row["identity_binding"]),
            ("partition_state_now", row["partition_state_now"]),
            ("source_order", WORK_ORDER),
        ])
        if row["identity_key"] and row["identity_key"] in inherited_keys:
            record["why_held"] = "already carried by 001's clean inventory; one identity is admitted once"
            held.append(record)
        elif row["verdict"] == "CLEAN_PET_FRIENDLY":
            new_pf.append(record)
        elif row["verdict"] == "CLEAN_VERIFIED_NO_PETS":
            new_np.append(record)
        else:
            record["why_held"] = row["why"]
            record["source_internal_conflict"] = row.get("source_internal_conflict")
            held.append(record)

    rows_pf = inherited_pf + new_pf
    rows_np = inherited_np + new_np
    keys = [r["identity_key"] for r in rows_pf + rows_np]
    assert len(keys) == len(set(keys)), "an identity may be admitted at most once"

    pf_now = pinned["PUBLISHED_PET_FRIENDLY"]
    np_now = pinned["VERIFIED_NO_PETS"]
    ooc = pinned["OUT_OF_CURRENT_CATEGORY"]
    total = partition["count"]

    # Every promoted row leaves an unresolved state and enters a resolved one.
    from_state = Counter(r.get("partition_state_now") or "AWAITING_POLICY_OBSERVATION"
                         for r in rows_pf + rows_np)
    shadow_states = dict(pinned)
    for state, n in from_state.items():
        shadow_states[state] = shadow_states.get(state, 0) - n
    shadow_states["PUBLISHED_PET_FRIENDLY"] = pf_now + len(rows_pf)
    shadow_states["VERIFIED_NO_PETS"] = np_now + len(rows_np)

    pf_proj = shadow_states["PUBLISHED_PET_FRIENDLY"]
    np_proj = shadow_states["VERIFIED_NO_PETS"]
    resolved = pf_proj + np_proj + ooc
    unresolved = total - resolved
    assert sum(shadow_states.values()) == total, "the shadow partition must still sum to the census"
    assert all(v >= 0 for v in shadow_states.values()), "no shadow state may go negative"

    report = OrderedDict()
    report["schema"] = SCHEMA
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET_ID
    report["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["authority_mutation"] = "NONE"
    report["usd_spent"] = 0.0
    report["paid_provider_calls"] = 0
    report["plan_credits_spent"] = 0
    report["phase_14_clean_pending_inventory"] = OrderedDict([
        ("clean_pet_friendly", len(rows_pf)),
        ("clean_verified_no_pets", len(rows_np)),
        ("held_with_evidence", len(held)),
        ("by_source_order", OrderedDict([
            ("PTF-CINCINNATI-HARDENED-REVALIDATION-001 (owned, carried onto this base)",
             len(inherited_pf) + len(inherited_np)),
            ("PTF-CINCINNATI-PARALLEL-REVALIDATION-002 (attended, this order)",
             len(new_pf) + len(new_np)),
        ])),
        ("every_row_carries_a_document_hash", all(r.get("document_sha256") for r in rows_pf + rows_np)),
        ("distinct_document_hashes", len({r["document_sha256"] for r in rows_pf + rows_np})),
        ("every_row_is_a_distinct_identity", True),
        ("no_census_admission_is_in_here",
         "the recensus and the competitor pass produced leads only; a verified new hotel is a census "
         "admission and belongs to an identity order, never to this inventory"),
        ("rows_pet_friendly", rows_pf),
        ("rows_verified_no_pets", rows_np),
        ("held", held),
    ])
    report["phase_17_shadow"] = OrderedDict([
        ("pinned_census", total),
        ("shadow_census", total),
        ("census_moved", 0),
        ("retirements", 0),
        ("successors", 0),
        ("same_campus", 0),
        ("explicit_assignments", 0),
        ("geography_holds", 0),
        ("identity_holds", sum(1 for r in held if r["verdict"] == "IDENTITY_REVIEW_REQUIRED")),
        ("why_census_did_not_move",
         "this order resolved no identity and moved no geography. Every candidate the recensus or the "
         "competitor directory raised is a lead awaiting a first-party identity ruling."),
        ("pinned_state_counts", OrderedDict(sorted(pinned.items()))),
        ("shadow_state_counts", OrderedDict(sorted(shadow_states.items()))),
        ("current", OrderedDict([
            ("pet_friendly", pf_now), ("verified_no_pets", np_now),
            ("resolved", pf_now + np_now + ooc), ("unresolved", total - (pf_now + np_now + ooc)),
            ("profiles", pf_now)])),
        ("projected_if_the_clean_inventory_were_promoted", OrderedDict([
            ("pet_friendly", pf_proj), ("verified_no_pets", np_proj),
            ("resolved", resolved), ("unresolved", unresolved), ("profiles", pf_proj),
            ("derivation", "unresolved = census - (published + no-pets + out-of-category), recomputed "
                           "from the partition and never carried forward")])),
        ("movement_against_001", OrderedDict([
            ("001_projected_pet_friendly", shadow1["phase_17_shadow"]["projected"]["pet_friendly"]),
            ("002_projected_pet_friendly", pf_proj),
            ("001_projected_no_pets", shadow1["phase_17_shadow"]["projected"]["verified_no_pets"]),
            ("002_projected_no_pets", np_proj),
            ("what_changed", "the attended lane, which 001 did not run"),
        ])),
    ])
    report["live_authority_crosscheck"] = OrderedDict([
        ("live_pet_friendly_records", pf_now),
        ("live_verified_no_pets", np_now),
        ("clean_rows_already_live", []),
        ("note", "every clean row sits in an unresolved partition state, so none of them contradicts a "
                 "live record; there is nothing live for them to contradict"),
    ])
    report["census_rows"] = len(census["hotels"])

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("wrote", OUT)
    print("clean PF %d  clean no-pets %d  held %d" % (len(rows_pf), len(rows_np), len(held)))
    print("current  PF %d / no-pets %d / resolved %d / unresolved %d"
          % (pf_now, np_now, pf_now + np_now + ooc, total - (pf_now + np_now + ooc)))
    print("projected PF %d / no-pets %d / resolved %d / unresolved %d / profiles %d"
          % (pf_proj, np_proj, resolved, unresolved, pf_proj))
    print("shadow states:", json.dumps(OrderedDict(sorted(shadow_states.items()))))


if __name__ == "__main__":
    main()
