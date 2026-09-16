"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 28: V1 vs V2 diagnostic (READ-ONLY comparison, after V2 is sealed).

V2 was rebuilt from zero; nothing here feeds V2. This helper reads the Tampa V1 final partition from the V1
branch's COMMIT (git show, worktree untouched) and V2's final partition, and compares them identity by
identity: which V1 published rows V2 also publishes, which V2 holds or reverses, and which V2 resolved that V1
left unresolved. Identity keys are compared exactly; a key present on one side only is reported, never matched
by name.

Output: launch_packages/pettripfinder/markets/reports/tampa_fl_v2_v1_diagnostic_001.json
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
V1_REPO = r"C:\Atlas-Tampa-FL-Hardened-V1"
V1_COMMIT = "f92077f8"
V1_PATH = "atlas-dashboard/launch_packages/pettripfinder/markets/staging/tampa-fl/launch_package/tampa_fl_final_partition_001.json"
V2_PATH = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "tampa-fl", "launch_package",
                       "tampa_fl_final_partition_v2_001.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports", "tampa_fl_v2_v1_diagnostic_001.json")
#: The mission's own historical Tampa V1 baseline, quoted verbatim.
V1_MISSION_BASELINE = OrderedDict([("census", 580), ("pet_friendly", 30), ("no_pets", 4), ("resolved", 34),
                                   ("unresolved", 546), ("resolution_rate", 0.059), ("firecrawl_wired", False)])


def main():
    v1 = json.loads(subprocess.run(["git", "show", "%s:%s" % (V1_COMMIT, V1_PATH)], cwd=V1_REPO, capture_output=True,
                                   check=True).stdout.decode("utf-8-sig"))
    v2 = json.load(open(V2_PATH, encoding="utf-8"))
    s1 = {i["identity_key"]: i["final_state"] for i in v1["items"]}
    s2 = {i["identity_key"]: i["final_state"] for i in v2["items"]}
    pub = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS")
    both = sorted(set(s1) & set(s2))
    transitions = Counter("%s -> %s" % (s1[k], s2[k]) for k in both)
    v1_published_v2_not = [OrderedDict([("identity_key", k), ("v1", s1[k]), ("v2", s2[k])])
                           for k in both if s1[k] in pub and s2[k] != s1[k]]
    v1_pf = sum(1 for v in s1.values() if v == "PUBLISHED_PET_FRIENDLY")
    v1_np = sum(1 for v in s1.values() if v == "VERIFIED_NO_PETS")
    v2_pf = sum(1 for v in s2.values() if v == "PUBLISHED_PET_FRIENDLY")
    v2_np = sum(1 for v in s2.values() if v == "VERIFIED_NO_PETS")
    doc = OrderedDict([
        ("schema", "ptf-v1-v2-diagnostic/1.0"), ("work_order", "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"),
        ("v1_source", "%s@%s (read by git show from C:\\Atlas-Tampa-FL-Hardened-V1; that worktree was not modified)"
         % (V1_PATH, V1_COMMIT)),
        ("v1_mission_baseline", V1_MISSION_BASELINE),
        ("v1_counts_from_v1s_own_partition", OrderedDict(sorted(Counter(s1.values()).items()))),
        ("v2_counts", OrderedDict(sorted(Counter(s2.values()).items()))),
        ("identity_keys", OrderedDict([("v1", len(s1)), ("v2", len(s2)), ("both", len(both)),
                                       ("v1_only", len(set(s1) - set(s2))), ("v2_only", len(set(s2) - set(s1)))])),
        ("state_transitions_on_shared_keys", OrderedDict(sorted(transitions.items()))),
        ("v1_published_not_identically_published_in_v2", v1_published_v2_not),
        ("v1_only_keys_sample", sorted(set(s1) - set(s2))[:40]),
        ("v2_only_keys_sample", sorted(set(s2) - set(s1))[:40]),
        ("delta_vs_v1_own_partition", OrderedDict([
            ("census", len(s2) - len(s1)), ("pet_friendly", v2_pf - v1_pf), ("no_pets", v2_np - v1_np),
            ("resolved", (v2_pf + v2_np) - (v1_pf + v1_np)),
        ])),
        ("delta_vs_v1_mission_baseline", OrderedDict([
            ("census", len(s2) - V1_MISSION_BASELINE["census"]),
            ("pet_friendly", v2_pf - V1_MISSION_BASELINE["pet_friendly"]),
            ("no_pets", v2_np - V1_MISSION_BASELINE["no_pets"]),
            ("resolved", (v2_pf + v2_np) - V1_MISSION_BASELINE["resolved"]),
            ("unresolved", (len(s2) - v2_pf - v2_np) - V1_MISSION_BASELINE["unresolved"]),
        ])),
        ("v2_not_manipulated_for_comparison",
         "V2 was rebuilt from zero and sealed before this diagnostic ran; nothing here fed back into V2's "
         "census, routing, acquisition or policy adjudication."),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps({k: doc[k] for k in ("v1_counts_from_v1s_own_partition", "v2_counts", "identity_keys")}))
    print("v1 published, v2 differs:", len(v1_published_v2_not), v1_published_v2_not[:12])
    print("transitions:", dict(transitions.most_common(12)))
    print("delta vs v1 own partition:", doc["delta_vs_v1_own_partition"])
    print("delta vs v1 mission baseline:", doc["delta_vs_v1_mission_baseline"])


if __name__ == "__main__":
    main()
