"""PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021.

Marriott serves two property-page templates. The locator list saw one of them,
so three of seventeen Milwaukee properties fell through to the generic walk --
and on Marriott the generic walk tends to land on the FAQ, which is
property-bound, well-formed, and not always as complete as the property's own
Pet Policy panel.

WHAT THESE TESTS GUARD
----------------------
Two layers, and both were wrong in the same direction.

The LOCATOR now binds the accordion panel as well as the icon container, and
the fourteen pages that always worked must go on working unchanged -- that is
the freeze half, and it is the half a locator change most easily breaks.

The READER now refuses to assert a single ``pet_fee`` when the block plainly
states components the frozen schema cannot carry together. Correcting the
locator alone would have moved the understatement one layer down rather than
ending it: The Trade's own panel says "$125 deposit + $20 daily pet fee" and
the charge patterns match neither, so a complete block still produced
"$125 per stay" and withheld nothing.

The corpus is real persisted captures from the 020 run, never hand-written
approximations, except where a test needs a decoy that no real page provides.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import html as LH

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.acquisition import marriott_template_021 as T    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.contracts import enums                           # noqa: E402
from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE


def report():
    return json.loads(T.REPORT.read_text(encoding="utf-8-sig"))


def queue():
    return json.loads(T.QUEUE.read_text(encoding="utf-8-sig"))


def capture_html(name):
    attempt = D._attempt_dir_for(T.RUN_ROOT, D._slug_of(name))
    assert attempt is not None, "no persisted capture for %r" % name
    return (attempt / "rendered.html").read_text(encoding="utf-8",
                                                 errors="replace")


# --------------------------------------------------------------------------- #
# Phase 3 -- the fixed corpus, drawn from real captures.
# --------------------------------------------------------------------------- #

ACCORDION_SUBJECTS = ("The Trade, Autograph Collection",
                      "The Westin Milwaukee",
                      "Milwaukee Marriott Downtown")

ICON_SUBJECTS = ("Hotel Metro, Autograph Collection",
                 "Residence Inn by Marriott Milwaukee West",
                 "TownePlace Suites by Marriott Milwaukee Oak Creek")

REFUSAL_SUBJECTS = ("Milwaukee Marriott Downtown",
                    "Renaissance Milwaukee West Hotel")


def test_the_corpus_covers_every_case_the_work_order_requires():
    """The corpus is not a convenience sample.

    It has to contain the known correctness case, every accordion page,
    representative icon successes, a refusal, and a page carrying the i18n
    decoy -- otherwise a passing suite would prove less than it appears to.
    """
    rows = {r["canonical_name"]: r for r in report()["rows"]}
    assert "The Trade, Autograph Collection" in rows
    accordion = [r for r in rows.values() if r["template"] == T.TEMPLATE_ACCORDION]
    assert {r["canonical_name"] for r in accordion} == set(ACCORDION_SUBJECTS)
    assert all(rows[n]["template"] == T.TEMPLATE_ICON for n in ICON_SUBJECTS)
    assert any(D.states_a_refusal(rows[n]["corrected_block"])
               for n in REFUSAL_SUBJECTS)
    # A page whose script carries the decoy, so the exclusion test is real.
    assert any(r["i18n_decoys"] > 0 for r in rows.values())


# --------------------------------------------------------------------------- #
# 1. The fourteen that always worked still work, unchanged.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ICON_SUBJECTS)
def test_icon_container_pages_still_locate_identically(name):
    html = capture_html(name)
    old = T.locate_offline(html, T.OLD_STRUCTURAL_XPATHS)
    new = T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS)
    assert old.found and new.found
    assert new.strategy == "pet_policy_heading_parent"
    assert new.text == old.text


def test_no_icon_container_page_changed_at_all():
    """The freeze, across every icon page in the corpus rather than a sample."""
    for row in report()["rows"]:
        if row["template"] != T.TEMPLATE_ICON:
            continue
        html = capture_html(row["canonical_name"])
        old = T.locate_offline(html, T.OLD_STRUCTURAL_XPATHS)
        new = T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS)
        assert new.text == old.text, row["canonical_name"]
        assert new.strategy == "pet_policy_heading_parent"


def test_the_new_locator_is_appended_and_does_not_displace_the_old_one():
    ids = [locator_id for locator_id, _ in MS.POLICY_LOCATORS]
    assert ids[0] == "pet_policy_heading_parent"
    assert ids[1] == "pet_policy_accordion_panel"
    assert "hotel_info_pet_icon_block" in ids and "any_pet_icon_block" in ids


# --------------------------------------------------------------------------- #
# 2. The accordion pages now locate.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ACCORDION_SUBJECTS)
def test_accordion_pages_locate_under_the_new_locator(name):
    html = capture_html(name)
    assert not T.locate_offline(html, T.OLD_STRUCTURAL_XPATHS).found
    new = T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS)
    assert new.found
    assert new.strategy == "pet_policy_accordion_panel"
    assert new.text.startswith("Pet Policy")


def test_the_accordion_block_excludes_its_sibling_panels():
    """Parking, Valet and Policies and Payments sit in the same accordion."""
    text = T.locate_offline(capture_html("The Trade, Autograph Collection"),
                            T.NEW_STRUCTURAL_XPATHS).text
    for sibling in ("Valet", "Parking", "Accessible", "Environmental"):
        assert sibling not in text


def test_every_marriott_capture_locates_under_the_new_locator():
    doc = report()
    assert doc["old_locator_successes"] == 14
    assert doc["new_locator_successes"] == doc["captures_scanned"] == 17


# --------------------------------------------------------------------------- #
# 3. Decoys.
# --------------------------------------------------------------------------- #

def test_the_i18n_dictionary_is_never_selected():
    """``"hws.petPolicy":"Pet Policy"`` lives in a <script>.

    An element selector cannot reach it, and this proves that on the real
    pages rather than by argument.
    """
    for name in ACCORDION_SUBJECTS + ICON_SUBJECTS:
        html = capture_html(name)
        hit = T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS)
        assert "hws." not in hit.text
        assert "petPolicy" not in hit.text


def test_a_script_only_pet_policy_string_locates_nothing():
    """A page whose ONLY 'Pet Policy' is a script string must yield no block."""
    html = ('<html><body><script>var t={"hws.petPolicy":"Pet Policy",'
            '"hws.parking":"Parking"};</script><p>Free parking.</p></body></html>')
    assert not T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS).found


def test_a_bold_that_merely_mentions_pets_is_not_a_heading():
    """The heading text must be exactly 'Pet Policy'."""
    html = ("<html><body><div><b>Pet Policy and Parking</b>"
            "<p>Pets welcome for $25 per night.</p></div></body></html>")
    assert not T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS).found


def test_the_locator_carries_no_property_specific_logic():
    """No hotel name and no Marriott property code anywhere in the selectors."""
    blob = " ".join(selector for _, selector in MS.POLICY_LOCATORS)
    for banned in ("mkedd", "mkeiw", "mkedn", "Trade", "Westin", "Autograph"):
        assert banned.lower() not in blob.lower()
    assert not re.search(r"mke[a-z]{2}", blob, re.I)
    source = (REPO / "scripts" / "pettripfinder" / "brightdata"
              / "marriott_surface.py").read_text(encoding="utf-8")
    code_only = "\n".join(line for line in source.splitlines()
                          if not line.lstrip().startswith("#"))
    assert not re.search(r"[\"'](?:mke[a-z]{2})[\"']", code_only, re.I)


# --------------------------------------------------------------------------- #
# 4. The Trade safety test.
# --------------------------------------------------------------------------- #

def trade_block():
    return T.locate_offline(capture_html("The Trade, Autograph Collection"),
                            T.NEW_STRUCTURAL_XPATHS).text


def test_the_trade_block_preserves_both_charge_concepts():
    """The Phase 5 bar: the block must not be reducible to one charge."""
    block = trade_block()
    assert "deposit" in block.lower()
    assert "$125" in block
    assert "$20" in block
    assert re.search(r"\bdaily\b", block, re.I)


def test_the_trade_block_is_not_the_faq_sentence():
    block = trade_block()
    assert "Yes, pets are welcome at" not in block
    assert block.startswith("Pet Policy")


def test_the_trade_no_longer_asserts_a_single_understated_fee():
    """The success criterion, stated as the system's own output.

    A complete block is not enough on its own: the reader has to decline the
    fee rather than publish whichever component happened to parse.
    """
    reading = MS.parse_policy_block(trade_block(), locator_id="t")
    result = MS.to_extraction(reading, location="t")
    assert "pet_fee" not in result.extraction
    assert "fee_basis" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert result.withheld["fee_basis"] == enums.SCHEMA_CANNOT_REPRESENT
    kinds = {u["kind"] for u in reading.unrepresented}
    assert "recurring_charge_not_represented" in kinds
    assert "deposit_not_represented" in kinds


def test_the_trade_still_yields_the_facts_that_are_safe():
    """Withholding the fee must not throw away the rest of the policy."""
    result = MS.to_extraction(
        MS.parse_policy_block(trade_block(), locator_id="t"), location="t")
    assert result.extraction["pets_allowed"] is True
    assert result.extraction["weight_limit"] == {"value": 100.0, "unit": "lb"}
    assert result.extraction["pet_count_limit"] == 2


def test_no_evidence_quote_survives_for_a_withheld_fee():
    """A quote that vouches for a field nobody asserts is a loose end."""
    result = MS.to_extraction(
        MS.parse_policy_block(trade_block(), locator_id="t"), location="t")
    for item in result.evidence:
        assert "pet_fee" not in item["field_refs"]
        assert "fee_basis" not in item["field_refs"]


# --------------------------------------------------------------------------- #
# The withholding rule itself.
# --------------------------------------------------------------------------- #

def test_a_single_clean_charge_is_still_asserted():
    """The guard must not swallow the ordinary case."""
    block = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $75.00 "
             "Maximum Pet Weight: 40.0lbs")
    result = MS.to_extraction(MS.parse_policy_block(block, locator_id="t"),
                              location="t")
    assert result.extraction["pet_fee"] == 7500
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert "pet_fee" not in result.withheld


def test_a_tiered_fee_withholds_rather_than_taking_the_first_tier():
    """A 6-night stay costs the second tier; asserting the first understates."""
    block = ("Pet Policy Pets Welcome 0-5 nights $75 5+ $150 "
             "Non-Refundable Pet Fee Per Stay: $75.00")
    reading = MS.parse_policy_block(block, locator_id="t")
    result = MS.to_extraction(reading, location="t")
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert any(u["amount_minor"] == 15000 for u in reading.unrepresented)


def test_a_refusal_is_unaffected_by_the_fee_guard():
    result = MS.to_extraction(
        MS.parse_policy_block("Pet Policy Pets Not Allowed", locator_id="t"),
        location="t")
    assert result.extraction["pets_allowed"] is False
    assert "pet_fee" not in result.extraction


@pytest.mark.parametrize("name", REFUSAL_SUBJECTS)
def test_refusal_properties_still_locate_and_read_as_refusals(name):
    block = T.locate_offline(capture_html(name), T.NEW_STRUCTURAL_XPATHS).text
    assert block
    result = MS.to_extraction(MS.parse_policy_block(block, locator_id="t"),
                              location="t")
    assert result.extraction["pets_allowed"] is False


# --------------------------------------------------------------------------- #
# Phase 7 -- the queue.
# --------------------------------------------------------------------------- #

def test_the_queue_names_exactly_the_materially_wrong_records():
    doc = queue()
    assert doc["count"] == 3
    assert {i["canonical_name"] for i in doc["items"]} == {
        "The Trade, Autograph Collection",
        "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek",
        "Sheraton Milwaukee Brookfield Hotel"}


def test_the_trade_is_explicitly_classified():
    item = next(i for i in queue()["items"]
                if i["canonical_name"] == "The Trade, Autograph Collection")
    assert item["material_issue"] == T.FEE_UNDERSTATED


def test_a_record_can_be_queued_without_its_block_changing():
    """Sheraton's block is UNCHANGED and its stored reading is still unsafe.

    A block-only comparison would have missed it entirely, which is why the
    queue compares against what the stored RECORD asserts.
    """
    rows = {r["canonical_name"]: r for r in report()["rows"]}
    sheraton = rows["Sheraton Milwaukee Brookfield Hotel"]
    assert sheraton["change_class"] == T.UNCHANGED
    assert sheraton["material_issue"] == T.FEE_COMPONENT_MISSING
    assert "pet_fee" in sheraton["stored_record_fields"]


def test_the_fourteen_untouched_records_are_not_queued():
    doc = report()
    unaffected = [r for r in doc["rows"]
                  if r["material_issue"] == T.NO_MATERIAL_CHANGE]
    assert len(unaffected) == 14
    assert not set(doc["review_queue"]) & {r["canonical_name"] for r in unaffected}


def test_the_queue_is_a_queue_and_not_a_mutation():
    doc = queue()
    assert doc["published"] is False
    assert doc["founder_approved"] is False
    assert doc["requires_reacquisition"] is False
    assert report()["observations_updated"] is False


# --------------------------------------------------------------------------- #
# Phase 8 -- historical safety.
# --------------------------------------------------------------------------- #

def test_no_persisted_policy_block_was_rewritten():
    """The captures are the evidence; 021 reads them and edits none.

    Their mtimes all predate this work order's report.
    """
    doc = report()
    written = T.REPORT.stat().st_mtime
    for row in doc["rows"]:
        attempt = D._attempt_dir_for(T.RUN_ROOT, D._slug_of(row["canonical_name"]))
        block = attempt / PL.BLOCK_ARTIFACT
        assert block.is_file()
        assert block.stat().st_mtime < written, row["canonical_name"]


def test_the_020_reports_were_not_edited():
    for path in (D.RUN_REPORT, D.DECISION_REPORT):
        changed = subprocess.run(
            ["git", "status", "--porcelain", "--",
             str(path.relative_to(REPO.parent))],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
        assert changed == "", "%s was modified by 021" % path.name


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_the_marriott_route_is_unchanged():
    route = REGISTRY.resolve(
        brand="MARRIOTT",
        url="https://www.marriott.com/en-us/hotels/mkeak-x/overview/")
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert route.reader == "marriott"


def test_the_other_brands_are_unchanged():
    for brand, reader in (("CHOICE", "choice_static"), ("WYNDHAM", "wyndham"),
                          ("IHG", "ihg")):
        route = REGISTRY.resolve(brand=brand, url="https://example.com/x")
        assert route.provider == PROVIDERS.FIRECRAWL and route.reader == reader


def test_routes_json_was_not_written():
    last = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()
    assert last and last != head


def test_the_canonical_locator_contract_is_untouched():
    """021 changed a brand selector list, not the persistence contract."""
    assert PL.CONTRACT == "ptf-policy-locator/1.0"
    assert PL.BLOCK_ARTIFACT == "policy-block.txt"
    assert PL.LOCATOR_ARTIFACT == "locator.json"
    assert PL.REPLAYED == "REPLAYED_FROM_CANONICAL_ARTIFACT"
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    assert changed == ""


def test_the_generic_locator_and_its_bounds_are_untouched():
    for path in (                 # policy_reading.py left this freeze in 024, which changed
                 # the generic reader deliberately. This work order still
                 # changed nothing there.
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py"):
        changed = subprocess.run(
            ["git", "status", "--porcelain", "--", path],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
        assert changed == "", "%s was modified by 021" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()

def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found


def test_nothing_was_published():
    doc = report()
    assert doc["published"] is False
    assert doc["authority_written"] is False
    assert doc["routes_changed"] is False
