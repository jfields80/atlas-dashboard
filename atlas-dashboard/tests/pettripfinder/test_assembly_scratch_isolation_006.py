"""PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 -- two pytest runs may not share a build tree.

WHAT HAPPENED

Closing the Nashville launch produced 39 fixture errors in the two modules that
render the whole multi-market site. They looked like assembler defects: a
rendered Columbus profile missing from one run's fragment tree, a shared asset
missing from the other's composed bundle -- in both cases a file the build had
just written.

They were not. Both modules built into ONE hard-coded absolute path
(``C:/t/ptf045t`` and ``C:/t/ptf046t``) and both tear that path down with
``shutil.rmtree``. The regression rule says to prove a new failure by running
the suite at HEAD and again in a scratch WORKTREE at the parent commit, and the
obvious way to do that is to run both at once. Two runs then wrote into and
deleted the same directory.

The evidence is in the run log, and it is unambiguous:

    ran alone, HEAD             18m 56s   29 failed, 222 passed,  0 errors
    ran alone, parent commit    16m 57s    7 failed, 244 passed,  0 errors
    the two run CONCURRENTLY     3m 00s   21 failed, 191 passed, 39 errors
                                 1m 33s   15 failed, 197 passed, 39 errors

Identical error counts, finishing two seconds apart, in a fraction of the time a
real assembly takes -- because each build died partway through when the other
deleted its tree. Neither run alone produced a single error.

So the harness made the PRESCRIBED workflow unsafe, and did it in a way that
reads as a defect in the thing being tested. These tests keep the roots
process-private.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from pettripfinder.conftest import assembly_scratch
from pettripfinder.test_global_deployment_architecture_045 import SCRATCH as SCRATCH_045
from pettripfinder.test_launch_participation_046 import SCRATCH as SCRATCH_046

REPO = Path(__file__).resolve().parents[2]


def test_the_two_heavy_modules_do_not_share_a_build_root():
    """The exact collision. They ran into the same directory before this."""
    assert SCRATCH_045 != SCRATCH_046


def test_each_root_is_private_to_this_process():
    assert str(os.getpid()) in SCRATCH_045.name
    assert str(os.getpid()) in SCRATCH_046.name


def test_another_process_gets_a_different_root():
    """Asserted by ASKING another interpreter, not by reasoning about getpid.

    A root that merely looks unique is what the fixed path looked like too.
    """
    code = ("import sys; sys.path.insert(0, %r); "
            "from pettripfinder.conftest import assembly_scratch; "
            "print(assembly_scratch('p45'))" % str(REPO / "tests"))
    other = subprocess.run([sys.executable, "-c", code], cwd=str(REPO),
                           capture_output=True, check=True).stdout.decode().strip()
    assert other != str(SCRATCH_045)
    assert other.startswith(str(SCRATCH_045.parent))


def test_the_root_stays_short_enough_for_a_deep_windows_tree():
    """The other cause of a missing file, and the reason the root is not
    somewhere tidier: the generated tree nests deeply enough that a long root
    trips the 260-character limit mid-build, which also surfaces as a file that
    should exist and does not."""
    deepest = (assembly_scratch("p45") / "prod" / ".assemble_work" / "fragments"
               / "cleveland-akron-canton-oh" / "pet-friendly-hotels"
               / "residence-inn-by-marriott-cleveland-downtown" / "index.html")
    assert len(str(deepest)) < 200, str(deepest)


def test_no_module_hard_codes_a_machine_wide_build_root():
    """The rule, not just the two known instances."""
    offenders = []
    for path in sorted((REPO / "tests" / "pettripfinder").rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "SCRATCH" in line and "=" in line and "assembly_scratch" not in line:
                if ":/t/" in line or ":\\\\t\\\\" in line:
                    offenders.append("%s: %s" % (path.name, line.strip()))
    assert offenders == []
