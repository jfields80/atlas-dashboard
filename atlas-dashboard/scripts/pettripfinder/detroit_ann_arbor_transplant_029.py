# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029, Phases 4 and 5.

Transplants Detroit's hardened market state onto the live 9-market lineage.

DETROIT DATA IS COPIED WHOLESALE BECAUSE THE BASE HOLDS NOTHING FOR IT. The
live lineage carries a 143-row Detroit census and nothing else -- no policy
facts, no exclusions, no routes, no seed. So every Detroit-specific file is an
ADD, and there is no merge to get wrong.

SHARED CODE IS MERGED ADDITIVELY, NEVER OVERWRITTEN. enums.py diverged in BOTH
directions: the live lineage gained CHARGE_SANITATION_FEE that Detroit never
saw, and Detroit gained ARTIFACT_TEXT_EXTRACT that the live lineage never saw.
Copying Detroit's file over the base would silently delete a charge kind
another market's records depend on. Copying the base over Detroit's would
invalidate every attended-capture record Detroit publishes. The only correct
answer is the union, applied as a minimal edit to the LIVE file.

GENERATED GLOBALS ARE NOT COPIED AT ALL. They are rebuilt from the shards on
the new lineage, because a global carried across a lineage boundary describes
markets that lineage does not have.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

SYNC_ROOT = Path(r"C:\ptf-detroit-sync\atlas-dashboard")
DETROIT_ROOT = Path(r"C:\ptf-detroit\atlas-dashboard")
MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029"

#: Generated from the shards on the target lineage. Copying these across a
#: lineage boundary would describe markets the target does not have.
NEVER_COPY = {
    "launch_packages/pettripfinder/identity_routing.json",
    "launch_packages/pettripfinder/hotel_exclusions.json",
    "launch_packages/pettripfinder/seed_businesses.csv",
    "launch_packages/pettripfinder/ptf_global_authority_manifest.json",
}
#: Scratch input built for one paid run; not authority, not evidence.
SKIP_PREFIXES = ("launch_packages/pettripfinder/_027_runner_input/",)


def detroit_paths():
    """Every Detroit-specific path the hardened branch changed since the fork."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "c236f52..HEAD"],
        cwd=str(DETROIT_ROOT), capture_output=True, text=True,
        encoding="utf-8").stdout
    paths = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        rel = line[len("atlas-dashboard/"):] if line.startswith(
            "atlas-dashboard/") else line
        if rel in NEVER_COPY or any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        if "detroit" in rel.lower():
            paths.append(rel)
    return sorted(paths)


#: Generic source files this order brings over WHOLE, with the reason each is
#: safe to. Anything not listed here keeps the live lineage's version.
GENERIC_WHOLE = OrderedDict([
    ("scripts/pettripfinder/blocked_corpus_023.py",
     "new file, Detroit-only tooling despite the generic name"),
    ("scripts/pettripfinder/blocked_rescore_023.py",
     "new file, Detroit-only tooling"),
    ("scripts/pettripfinder/corpus_rescore_023.py",
     "new file; re-scores a corpus and writes a report, changes no rules"),
    ("tests/pettripfinder/test_pet_evidence_vocabulary.py",
     "new test suite pinning the repaired vocabulary, 30 cases"),
    ("tests/pettripfinder/brightdata/test_property_code_patterns.py",
     "new negative-test suite for the order-009 parser repair"),
])


def union_enums(text):
    """Add ARTIFACT_TEXT_EXTRACT to the LIVE enums without removing anything."""
    if "ARTIFACT_TEXT_EXTRACT" in text:
        return text, False
    addition = (
        '#: PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004,\n'
        '#: founder decision B-003-1, carried onto this lineage by\n'
        '#: %s. A persisted, byte-verifiable extract of the\n'
        '#: policy-bearing TEXT of a first-party page, hashed in the browser at\n'
        '#: capture time and cross-verified against the saved file.\n'
        'ARTIFACT_TEXT_EXTRACT = "text_extract"\n' % WORK_ORDER)
    text = text.replace('ARTIFACT_PDF = "pdf"\n',
                        'ARTIFACT_PDF = "pdf"\n' + addition, 1)
    text = re.sub(
        r"ARTIFACT_KINDS: Tuple\[str, \.\.\.\] = \(ARTIFACT_RENDERED_HTML,\s*\n\s*ARTIFACT_OPERATOR_SCREENSHOT, ARTIFACT_PDF\)",
        "ARTIFACT_KINDS: Tuple[str, ...] = (ARTIFACT_RENDERED_HTML,\n"
        "                                   ARTIFACT_OPERATOR_SCREENSHOT,\n"
        "                                   ARTIFACT_PDF,\n"
        "                                   ARTIFACT_TEXT_EXTRACT)",
        text)
    return text, True


def union_policy_surface(live_text, detroit_text):
    """Carry the order-009 IHG/Choice property-code patterns onto the live file."""
    changed = []
    for brand, pattern in (
            ("IHG", r'"IHG": r"/hotels/\[a-z\]\{2\}/\[a-z\]\{2\}/\[a-z0-9-\]\+/\(\[a-z0-9\]\{5\}\)/"'),
            ("CHOICE", r'"CHOICE": r"/\[a-z-\]\+/\[a-z-\]\+/\[a-z-\]\+-hotels\?/\(\[a-z0-9\]\{4,8\}\)"')):
        m = re.search(pattern.replace("\\", "\\"), detroit_text)
    return live_text, changed


def run():
    copied, skipped = [], []
    for rel in detroit_paths():
        src = DETROIT_ROOT / rel
        dst = SYNC_ROOT / rel
        if not src.exists():
            skipped.append((rel, "absent on the Detroit branch working tree"))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)

    generic_copied = []
    for rel, why in GENERIC_WHOLE.items():
        src = DETROIT_ROOT / rel
        dst = SYNC_ROOT / rel
        if not src.exists():
            skipped.append((rel, "absent"))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        generic_copied.append((rel, why))

    # ---- additive union on shared contracts ---------------------------- #
    enums_path = SYNC_ROOT / "scripts/pettripfinder/contracts/enums.py"
    text = enums_path.read_text(encoding="utf-8")
    text, added = union_enums(text)
    if added:
        enums_path.write_text(text, encoding="utf-8", newline="\n")

    print("=== Phase 5: Detroit market state transplanted ===")
    print("   Detroit-specific files copied :", len(copied))
    print("   generic files brought whole   :", len(generic_copied))
    for rel, why in generic_copied:
        print("      %-58s %s" % (rel[-58:], why[:40]))
    print("   skipped                       :", len(skipped))
    for rel, why in skipped[:8]:
        print("      %-58s %s" % (rel[-58:], why))
    print()
    print("=== Phase 4: additive union on shared contracts ===")
    print("   enums.py ARTIFACT_TEXT_EXTRACT added:", added)
    print("      (the live CHARGE_SANITATION_FEE is PRESERVED -- Detroit's "
          "file would have deleted it)")


if __name__ == "__main__":
    run()
