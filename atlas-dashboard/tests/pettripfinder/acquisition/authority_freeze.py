"""What "no Milwaukee policy authority exists" actually claimed.

Twenty-six work orders asserted it, and every one of them was right when it
was written: none of those passes was permitted to create authority, and the
absence of the file was the cheapest way to prove it.

Then the founder read the 036 review package and approved 96 records, and the
file exists on purpose. Read literally, those twenty-six assertions now say
"Milwaukee may never have a policy authority", which is not a claim any of them
made and not one the repository can keep.

So each is narrowed to what it meant: THIS WORK ORDER did not create authority.
That is a statement about a commit, and it is checked against the commit --
which stays true forever, including after some later pass legitimately creates
the file.

The two halves are separate on purpose:

* ``assert_commit_created_no_authority`` -- the historical claim, per commit.
* ``assert_authority_is_recorded_not_live`` -- the standing claim, which is the
  one that still protects a traveller: whatever authority exists is not live
  inventory until someone deliberately publishes it.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

#: Where Milwaukee's authority and its refusal registry live.
AUTHORITY = (REPO / "launch_packages" / "pettripfinder"
             / "hotel_policy_facts_milwaukee-wi.json")
EXCLUSIONS = REPO / "launch_packages" / "pettripfinder" / "hotel_exclusions.json"

#: The work order that created it, and the founder decision that authorised it.
CREATED_BY = "PTF-MILWAUKEE-FOUNDER-DECISION-036"
LEDGER = (REPO / "launch_packages" / "pettripfinder"
          / "milwaukee_founder_decisions_036.json")


def _touched_by(commit):
    return subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", commit],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.split()


def assert_commit_created_no_authority(commit):
    """That commit did not create or touch Milwaukee's policy authority."""
    for name in _touched_by(commit):
        assert "hotel_policy_facts" not in name or "milwaukee" not in name, \
            "%s touched %s" % (commit, name)


def assert_authority_is_recorded_not_live():
    """Whatever authority exists is recorded, and no page reads it.

    ``site_data.load_published_hotel_policy_facts`` returns {} for a package
    carrying ``published: false``, so this is enforced by the loader rather
    than by anyone remembering.
    """
    if not AUTHORITY.is_file():
        return
    doc = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert doc.get("published") is False, "Milwaukee authority claims to be live"
    from scripts.pettripfinder import site_data as SD
    assert SD.load_published_hotel_policy_facts("milwaukee-wi") == {}


def assert_every_authority_row_was_approved_by_a_human():
    """Nothing reaches authority on the strength of a review status."""
    if not AUTHORITY.is_file():
        return
    doc = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert LEDGER.is_file(), "authority exists with no decision ledger"
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    approved = {row["identity_key"] for row in ledger["decisions"]
                if row["decision"] == "APPROVE"}
    for record in doc["hotels"]:
        assert record["identity_key"] in approved, record["identity_key"]
        assert record["approval"]["operator"] == ledger["decided_by"]
