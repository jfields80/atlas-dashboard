"""PTF-ACQUISITION-BRAND-REPAIR-003 -- the repairs, and what they must not break.

Three of the tests here exist because the repair run itself produced a wrong
answer against a known property. Each is written from the exact wording that
caused it, because a regression test built from the real sentence is the only
kind that stays true when the pattern is rewritten again.
"""

from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import brand_repair_003 as R
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import client
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.brightdata import policy_surface as PS
from scripts.pettripfinder.brightdata import unlocker_capture as UC
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EV
from scripts.pettripfinder.policy import policy_observation as PO

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# --------------------------------------------------------------------------- #
# The lanes.
# --------------------------------------------------------------------------- #

def test_the_lane_sample_is_fifteen_of_pilot_002s_own_properties():
    sample = R.build_lane_sample()
    assert len(sample) == 15
    pilot_two = {r.identity_key for r in P2.build_sample()}
    assert all(r.identity_key in pilot_two for r in sample), \
        "a repair benchmarked on different hotels would measure the hotels"


def test_the_lanes_are_two_repairs_and_two_controls():
    assert [b for b, _, _ in R.LANES] == ["WYNDHAM", "CHOICE", "HILTON",
                                          "MARRIOTT"]
    assert dict((b, n) for b, n, _ in R.LANES) == {
        "WYNDHAM": 5, "CHOICE": 5, "HILTON": 3, "MARRIOTT": 2}
    whys = {b: why for b, _, why in R.LANES}
    assert "provider" in whys["CHOICE"]
    assert "reader" in whys["WYNDHAM"]
    assert whys["MARRIOTT"].startswith("control")


def test_only_choice_leaves_the_browser_api():
    assert set(R.PROVIDERS) == {"CHOICE"}
    assert R.PROVIDERS["CHOICE"] is UC


def test_the_unlocker_calls_itself_a_deterministic_fetch():
    """It is not a browser somebody drove; GAP-02 still stands for both."""
    assert R.CAPTURE_METHODS["CHOICE"] == "deterministic_fetch"
    assert R.CAPTURE_METHODS["CHOICE"] in PO.CAPTURE_METHODS


def test_the_production_targets_are_the_ones_the_work_order_set():
    assert R.TARGET_PRECISION == 95.0
    assert R.TARGET_RECALL == 85.0
    assert R.meets_target({"critical_precision_percent": 100.0,
                           "critical_recall_percent": 90.0})
    assert not R.meets_target({"critical_precision_percent": 100.0,
                               "critical_recall_percent": 84.9})
    assert not R.meets_target({"critical_precision_percent": None,
                               "critical_recall_percent": None})


# --------------------------------------------------------------------------- #
# Wyndham: text the page holds but never paints.
# --------------------------------------------------------------------------- #

def test_wyndham_has_a_brand_locator():
    assert "WYNDHAM" in PS.BRAND_LOCATORS
    selectors = [s for _, s in PS.BRAND_LOCATORS["WYNDHAM"]]
    assert ".pet-policy-desc" in selectors


def test_a_brand_locator_may_read_text_the_page_has_not_painted():
    """Wyndham's policy was in the hashed artifact all along, unrendered."""
    assert "el.textContent" in PS._BRAND_READ_SCRIPT
    assert "rendered" in PS._BRAND_READ_SCRIPT
    hit = PS.SurfaceHit(found=True, text="x", rendered=False)
    assert hit.to_dict()["rendered"] is False


_WYNDHAM_BLOCK = (
    "Service Animals - ADA-defined service animals are welcome free of charge. "
    "/ Dogs Allowed - 2 dogs max. 75lbs or less per pet. / Fees - 25 USD per "
    "pet per night. Max 75 USD per stay.")


def test_wyndham_wording_reads_completely():
    result = PR.to_extraction(PR.parse(_WYNDHAM_BLOCK), location="b")
    assert result.extraction["pets_allowed"] is True
    assert result.extraction["pet_fee"] == 2500
    assert result.extraction["fee_basis"] == enums.BASIS_PER_NIGHT
    assert result.extraction["fee_scope"] == enums.SCOPE_PER_PET
    assert result.extraction["pet_count_limit"] == 2
    assert result.extraction["weight_limit"] == {"value": 75.0, "unit": "lb"}
    assert result.extraction["species_allowed"] == ["dog"]


def test_a_ceiling_is_recorded_as_a_cap_and_never_as_the_price():
    """CEILING != PRICE is a founder rule."""
    result = PR.to_extraction(PR.parse(_WYNDHAM_BLOCK), location="b")
    assert result.extraction["fee_cap"]["amount_minor"] == 7500
    assert result.extraction["pet_fee"] == 2500


# --------------------------------------------------------------------------- #
# The three wrong answers this run produced.
# --------------------------------------------------------------------------- #

def test_a_refusal_that_contains_the_word_allowed_is_still_a_refusal():
    """Microtel North Canton. The reader called a no-pets hotel pet friendly.

    "Sorry no other pets are allowed" contains "pets are allowed". This is the
    mirror of a false VERIFIED_NO_PETS and is worse, because it publishes a
    pet-friendly listing for a property that refuses pets.
    """
    block = ("ADA defined service animals are welcome at this hotel. "
             "Sorry no other pets are allowed.")
    reading = PR.parse(block)
    assert reading.pets_allowed is False
    result = PR.to_extraction(reading, location="b")
    assert result.extraction["pets_allowed"] is False


@pytest.mark.parametrize("block,expected", [
    ("Sorry no other pets are allowed.", False),
    ("No additional pets are permitted.", False),
    ("Service animals welcome. No further pets allowed.", False),
    ("Pets Allowed - 2 pets max.", True),
    ("Dogs Allowed - 2 dogs max.", True),
    ("Pets permitted. 50.00 per stay.", True),
])
def test_negation_governs_an_acceptance(block, expected):
    assert PR.parse(block).pets_allowed is expected


def test_a_refundable_deposit_is_never_the_pet_fee():
    """Comfort Inn Canton. The reader published the $100 deposit as the fee.

    The page states both: "25.00 USD Per Pet per night" and "100.00 USD
    refundable deposit required". A guest told the deposit is the nightly fee
    is misinformed in the direction that costs them money.
    """
    block = ("General: Pets are Allowed. 25.00 USD Per Pet per night. "
             "100.00 USD refundable deposit required. A maximum of 30 pounds "
             "per Pet and 2 Pets per room.")
    result = PR.to_extraction(PR.parse(block), location="b")
    assert result.extraction["pet_fee"] == 2500
    assert result.extraction["fee_basis"] == enums.BASIS_PER_NIGHT
    assert result.extraction["pet_deposit"] == 10000


def test_a_charge_with_a_stated_basis_outranks_one_without():
    reading = PR.parse("Pets allowed. 25.00 USD per night. $100 pet deposit.")
    result = PR.to_extraction(reading, location="b")
    assert result.extraction.get("pet_fee") == 2500


def test_the_dearborn_contradiction_still_survives_every_change():
    """The case pilot-001 was built around, re-checked after each repair."""
    block = ("Pet Policy Pets Welcome Pet fee $20/day with $100/stay "
             "nonrefundable clean fee Non-Refundable Pet Fee Per Stay: $100.00 "
             "Non-Refundable Pet Fee Per Night: $20.00")
    result = PR.to_extraction(PR.parse(block), location="b")
    assert result.extraction["pet_fee"] == 2000
    assert "fee_basis" not in result.extraction
    assert result.withheld["fee_basis"] == enums.SOURCE_CONTRADICTORY
    assert result.extraction["cleaning_fee"] == 10000


def test_the_room_rate_hole_stays_shut_in_every_money_shape():
    for block in (
        "1 King Bed 4 Guests No Pets Allowed Discounted rate: $160 USD /night",
        "No Pets Allowed Member Rate 160.00 per night",
        "No Pets Allowed Strikethrough Rate: $172 Discounted rate: $160 /night",
    ):
        result = PR.to_extraction(PR.parse(block), location="b")
        assert "pet_fee" not in result.extraction, block


def test_the_marriott_control_reads_exactly_as_before():
    """Every repair must leave the brand that already worked untouched."""
    block = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00 "
             "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 1")
    result = PR.to_extraction(PR.parse(block), location="b")
    assert result.extraction == {
        "pets_allowed": True, "pet_fee": 15000, "fee_currency": "USD",
        "fee_basis": enums.BASIS_PER_STAY,
        "weight_limit": {"value": 50.0, "unit": "lb"},
        "pet_count_limit": 1, "pet_count_scope": enums.SCOPE_PER_ROOM}


# --------------------------------------------------------------------------- #
# The Web Unlocker lane.
# --------------------------------------------------------------------------- #

def test_the_unlocker_keeps_the_same_retry_contract():
    source = inspect.getsource(UC.capture_property)
    assert "BC.MAX_ATTEMPTS" in source
    assert "O.VALID" in source
    assert UC.UNLOCKER_ZONES, "one zone refusing does not mean the next will"


def test_the_unlocker_preserves_block_boundaries():
    """textContent-style fusion is the defect innerText fixed in the browser."""
    text = UC.html_to_text("<td>Pets allowed</td><td>Yes</td>")
    assert "Pets allowedYes" not in text
    assert "Pets allowed" in text and "Yes" in text


def test_the_unlocker_strips_scripts_before_reading():
    text = UC.html_to_text("<script>var pets='Pets Allowed: Yes';</script>"
                           "<p>Pets Allowed: No</p>")
    assert "var pets" not in text
    assert "Pets Allowed: No" in text


def test_the_unlocker_locator_is_bounded_and_policy_bearing():
    html = ("<html><body><p>Fitness center with weight equipment</p>"
            "<li><span>Pets</span><div>Pets Allowed: Yes General: Pets "
            "permitted. 50.00 per stay. Maximum of two pets per room.</div>"
            "</li></body></html>")
    hit = UC.locate_policy_in_html(html)
    assert hit.found
    assert "weight equipment" not in hit.text
    assert hit.container_chars <= PS.MAX_BLOCK_CHARS


def test_the_unlocker_finds_nothing_in_a_page_about_nothing():
    hit = UC.locate_policy_in_html("<html><body><p>Fitness center with "
                                   "cardiovascular and weight equipment</p>"
                                   "</body></html>")
    assert not hit.found


def test_an_unlocker_interstitial_is_never_a_page():
    assert "captcha resolve failed" in UC.DENIAL_MARKERS
    assert "just a moment" in UC.DENIAL_MARKERS
    for marker in ("access denied", "pardon our interruption"):
        assert marker in UC.DENIAL_MARKERS


def test_the_scrape_command_is_allowlisted_and_zones_info_is_not():
    assert ("scrape",) in client.ALLOWED_CLI_ARGS
    assert ("zones", "info") not in client.ALLOWED_CLI_ARGS
    with pytest.raises(client.BrightDataUsageError):
        client._default_runner(["zones", "info", "scraping_browser1"])


def test_the_unlocker_records_that_it_took_no_screenshot():
    source = inspect.getsource(UC._persist)
    assert "policy_section" in source
    assert "no browser" in source or "no viewport" in source


# --------------------------------------------------------------------------- #
# Re-derivation and authority.
# --------------------------------------------------------------------------- #

def test_rederivation_touches_no_network():
    source = inspect.getsource(R.rederive_journal)
    for network in ("connect_over_cdp", "async_playwright", "capture_property",
                    "probe_exit_country", "_run_scrape"):
        assert network not in source, network


def test_nothing_in_the_repair_promotes_or_publishes():
    for module in (R, UC):
        source = inspect.getsource(module)
        for forbidden in ("promote_", "publication_guard", "apply_decisions",
                          "PUBLISHED_PET_FRIENDLY"):
            assert forbidden not in source, (module.__name__, forbidden)


def test_the_repair_writes_only_to_its_own_raw_tree_and_reports():
    assert R.RAW_ROOT.parts[-4:] == ("worker_runs", "pettripfinder",
                                     R.PILOT_ID, "raw")
    for path in (R.SUMMARY_REPORT, R.PROPERTY_REPORT, R.LANE_REPORT):
        assert path.parent == R.REPORT_DIR
    assert R.PROGRESS_JOURNAL != P2.PROGRESS_JOURNAL


# --------------------------------------------------------------------------- #
# Committed outputs.
# --------------------------------------------------------------------------- #

def _load(path):
    if not path.exists():
        pytest.skip("%s has not been produced yet" % path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_repair_reports_carry_no_credential():
    for path in (R.SUMMARY_REPORT, R.PROPERTY_REPORT, R.LANE_REPORT):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert not client.contains_credential(text), path.name
        for shape in ("brd-customer", "superproxy", "wss://"):
            assert shape not in text, (path.name, shape)


def test_committed_repair_freezes_authority():
    summary = _load(R.SUMMARY_REPORT)
    for key in ("policy_authority_changed", "exclusions_changed", "seed_changed",
                "approvals_changed", "partition_changed",
                "routing_authority_changed", "promotion_performed"):
        assert summary[key] is False, key
    assert summary["false_verified_no_pets"] == 0


def test_committed_repair_quotes_are_contiguous_and_valid():
    report = _load(R.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        block = prop["policy_block_quote"]
        for item in prop["observation"]["evidence"]:
            assert EV.quote_is_contiguous(item["quote"], block), prop["slug"]
        PO.validate_observation(prop["observation"])
        assert set(prop["observation"]["extraction"]) <= PO.EXTRACTION_FIELDS


def test_committed_repair_artifacts_hash():
    report = _load(R.PROPERTY_REPORT)
    checked = 0
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        for name, entry in prop["artifacts"]["files"].items():
            if not isinstance(entry, dict) or "sha256" not in entry:
                continue
            assert _SHA256_RE.match(entry["sha256"])
            path = Path(entry["path"])
            if path.exists():
                assert BC.sha256_file(path) == entry["sha256"], path
                checked += 1
    if checked == 0:
        pytest.skip("the gitignored raw tree is not present here")


def test_no_repair_property_claims_pets_where_its_block_refuses():
    report = _load(R.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        block = (prop.get("policy_block_quote") or "").lower()
        pets = prop["observation"]["extraction"].get("pets_allowed")
        if pets is True:
            assert not re.search(r"\bno (?:other |additional )?pets?\b", block), \
                prop["slug"]
