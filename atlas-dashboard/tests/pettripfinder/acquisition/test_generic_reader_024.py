"""PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024.

023 held six Hilton records for two named defects. One was real and one was
not, and these tests guard both conclusions.

REAL: banded fees collapsed to one amount. ``_fee_is_tiered`` already refused
to publish a tiered fee, but every qualifier it knew required the word "for".
Hilton writes "$50(1-4 nights),$125(5+ nights)" and five Milwaukee properties
asserted an understated fee because of it. The generic reader also had no rule
at all for charge components it did not parse, so "$75 per pet ... Per Stay:
$150.00" published $150.

NOT REAL: the Spark "pre-emption". Its page publishes "Pets allowed Yes" and
nothing else -- the static walk finds the identical sixteen characters, and the
words that looked like a suppressed richer block live in a JavaScript label
dictionary. The tests below pin that the classifier now requires evidence of
the alternative it claims was suppressed.

The controls matter as much as the fixes. A withholding rule that fires on a
capped fee, a simple fee or a refusal would be worse than the defect it
replaced, because it would withhold facts the schema can hold.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import generic_reader_024 as G      # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H     # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL          # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR          # noqa: E402
from scripts.pettripfinder.contracts import enums                          # noqa: E402
from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE

SCHEMA = enums.SCHEMA_CANNOT_REPRESENT


def read(block):
    return G.read_generic(block)


def corpus_report():
    return json.loads(G.CORPUS_REPORT.read_text(encoding="utf-8-sig"))


def queue():
    return json.loads(G.QUEUE_REPORT.read_text(encoding="utf-8-sig"))


def dry():
    return json.loads(G.DRY_RUN_REPORT.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1-4. Banded and multi-component fees are withheld.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("block", [
    "Pets allowed Yes Deposit Yes. $50.00 Non-refundable Fee Other pet "
    "information $50(1-4 nights),$125(5+ nights)",
    "Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Other pet "
    "information $75 for the first four nights, $125 for 5+",
    "Pets allowed Yes. $75/stay 1-4 nights, $125/stay 5+ nights",
    "Pets allowed Yes. $50/stay for 1 night, $75/stay for 2-4 nights, "
    "$125/stay for 5+ nights",
])
def test_a_banded_fee_cannot_collapse_to_the_first_amount(block):
    # NARROWED by work order 034. The durable claim is that a banded
    # surface never collapses to ONE amount; it used to be made by
    # asserting the fee was withheld, which is the exact behaviour 034 was
    # commissioned to replace. Schema 1.2 has always been able to hold the
    # ladder, so the price is now carried in fee_tiers -- and the thing
    # that must never happen, publishing one rung as the fee, is asserted
    # directly.
    result = read(block)
    assert "pet_fee" not in result["extraction"]
    tiers = result["extraction"].get("fee_tiers") or []
    if tiers:
        amounts = [tier["amount_cents"] for tier in tiers]
        assert len(amounts) >= 2 and len(set(amounts)) >= 2
        assert "pet_fee" not in result["withheld"]
    else:
        assert result["withheld"]["pet_fee"] == SCHEMA
        assert result["withheld"]["fee_basis"] == SCHEMA


def test_the_highest_band_is_never_silently_dropped():
    """The failure in one sentence: a five-night stay cost $125, not $50."""
    block = ("Pets allowed Yes Deposit Yes. $50.00 Non-refundable Fee Other "
             "pet information $50(1-4 nights),$125(5+ nights)")
    assert read(block)["extraction"].get("pet_fee") != 5000


def test_incompatible_per_pet_and_per_stay_components_are_withheld():
    block = ("$75 per pet (dogs, fish, or birds) Non-Refundable Pet Fee Per "
             "Stay: $150.00")
    result = read(block)
    assert "pet_fee" not in result["extraction"]
    assert result["withheld"]["pet_fee"] == SCHEMA


def test_a_deposit_plus_recurring_fee_is_not_flattened():
    block = ("Pet Policy Pets Welcome. Pet deposit starts at $125 (may "
             "increase for suites) + $20 daily pet fee. Non-Refundable Pet Fee "
             "Per Stay: $125.00")
    result = read(block)
    assert "pet_fee" not in result["extraction"]
    assert result["withheld"]["pet_fee"] == SCHEMA


def test_components_are_never_summed():
    """$125 + $20 is not a pet fee of $145, and nothing may invent one."""
    block = "Pet deposit $125 plus $20 daily pet fee. Pet Fee Per Stay: $125.00"
    values = set(read(block)["extraction"].values())
    assert 14500 not in values and 26500 not in values


# --------------------------------------------------------------------------- #
# 5-6. The controls: nothing safe regresses.
# --------------------------------------------------------------------------- #

def test_a_simple_per_stay_fee_stays_structured():
    result = read("Pets Welcome. Non-refundable pet fee of $100 per stay.")
    assert result["extraction"]["pet_fee"] == 10000
    assert "pet_fee" not in result["withheld"]


def test_a_simple_per_night_fee_stays_structured():
    result = read("Pets Welcome. A $35 fee per night applies, maximum 2 pets "
                  "per room.")
    assert result["extraction"]["pet_fee"] == 3500
    assert result["extraction"]["fee_basis"] == enums.BASIS_PER_NIGHT


def test_a_capped_fee_is_not_mistaken_for_a_tier():
    """CEILING != PRICE. A cap has two amounts and is not a band."""
    result = read("Non-refundable 25 USD nightly for up to 2 pets. "
                  "Max 75 USD per stay")
    assert result["extraction"]["pet_fee"] == 2500
    assert result["extraction"]["fee_cap"]["amount_minor"] == 7500
    assert "pet_fee" not in result["withheld"]
    assert not PR._fee_is_tiered("Non-refundable 25 USD nightly for up to 2 "
                                 "pets. Max 75 USD per stay")


def test_a_single_priced_policy_mentioning_a_night_range_is_not_a_tier():
    """A band needs MORE THAN ONE distinct price as well as a qualifier."""
    assert not PR._fee_is_tiered("Pets welcome for 1-4 nights. $75 per stay.")


def test_a_terse_refusal_remains_valid():
    for block in ("Pets Not Allowed", "No, pets are not allowed at this hotel."):
        result = read(block)
        assert result["extraction"]["pets_allowed"] is False
        assert "pet_fee" not in result["extraction"]


def test_an_amenity_chip_remains_insufficient():
    result = read("Pets allowed Yes")
    assert "pet_fee" not in result["extraction"]
    assert result["withheld"]["pets_allowed"] == enums.ARTIFACT_INSUFFICIENT


def test_weight_and_count_and_species_survive_a_withheld_fee():
    """Withholding the fee must not throw away the rest of the policy."""
    block = ("Pets allowed Yes Deposit Yes. $50.00 Non-refundable Fee Max "
             "weight 100 lbs Other pet information $50(1-4 nights),$125(5+ "
             "nights) 2 Pet Max, Dog/Cat only")
    result = read(block)
    # The fee is carried as a ladder now (034); what this test is about is
    # that the REST of the policy survives whatever happens to the fee.
    assert "pet_fee" not in result["extraction"]
    assert result["extraction"]["weight_limit"]["value"] == 100.0
    assert result["extraction"]["pet_count_limit"] == 2


# --------------------------------------------------------------------------- #
# 7-8. The Hilton container: the defect that was not there.
# --------------------------------------------------------------------------- #

def test_the_spark_page_publishes_no_richer_block():
    """The evidence that retracts 023's pre-emption finding."""
    from scripts.pettripfinder.brightdata import unlocker_capture as UC
    attempt = (REPO / "data" / "acquisition" / H.PRODUCTION_RUN_ID
               / H.PRODUCTION_RUN_ID / "spark-by-hilton-milwaukee-airport"
               / "attempt-01")
    if not (attempt / "rendered.html").is_file():
        pytest.skip("the Spark capture is not on disk in this worktree")
    html = (attempt / "rendered.html").read_text(encoding="utf-8",
                                                 errors="replace")
    hit = UC.locate_policy_in_text(UC.html_to_text(html))
    assert hit.found
    assert hit.text.strip() == "Pets allowed Yes"


def test_a_thin_block_is_only_preemption_when_a_richer_one_exists():
    """The corrected classifier: the claim needs the alternative it names."""
    finding = H.audit_row({
        "canonical_name": "x", "policy_locator": "hilton_pet_panel",
        "usable_policy_detail": {"block_text": "Pets allowed Yes",
                                 "substantive_fields": [], "withheld_fields": [],
                                 "block_chars": 16, "rendered_html_path": ""}})
    assert finding["verdict"] == H.THIN_SURFACE
    assert finding["verdict"] != H.BRAND_CONTAINER_PREEMPTED


def test_the_hilton_audit_no_longer_claims_preemption():
    run = json.loads(H.RUN_REPORT.read_text(encoding="utf-8-sig"))
    audit = H.template_audit(run["rows"])
    assert audit["issue_counts"][H.BRAND_CONTAINER_PREEMPTED] == 0
    assert audit["issue_counts"][H.THIN_SURFACE] == 1


def test_a_refusal_is_never_called_thin():
    finding = H.audit_row({
        "canonical_name": "x", "policy_locator": "generic_signal_walk",
        "usable_policy_detail": {"block_text": "Pets Not Allowed",
                                 "substantive_fields": [], "withheld_fields": [],
                                 "block_chars": 16, "rendered_html_path": ""}})
    assert H.THIN_SURFACE not in finding["issues"]


# --------------------------------------------------------------------------- #
# 9-10. Marriott controls keep their proven semantics.
# --------------------------------------------------------------------------- #

def test_the_marriott_reader_still_withholds_the_trade():
    block = ("Pet Policy Pets Welcome. Pet deposit starts at $125 (may "
             "increase for suites) + $20 daily pet fee. Non-Refundable Pet Fee "
             "Per Stay: $125.00 Maximum Pet Weight: 100.0lbs Maximum Number of "
             "Pets in Room: 2")
    result = G.read_marriott(block)
    assert result["withheld"]["pet_fee"] == SCHEMA
    assert result["extraction"]["weight_limit"] == {"value": 100.0, "unit": "lb"}


def test_both_readers_now_agree_on_a_multi_component_block():
    """The point of generalising rather than duplicating: one semantic rule."""
    block = ("Pet Policy Pets Welcome. Pet deposit starts at $125 + $20 daily "
             "pet fee. Non-Refundable Pet Fee Per Stay: $125.00")
    assert G.read_generic(block)["withheld"]["pet_fee"] == SCHEMA
    assert G.read_marriott(block)["withheld"]["pet_fee"] == SCHEMA


def test_the_marriott_reader_still_structures_a_clean_single_charge():
    result = G.read_marriott("Pet Policy Pets Welcome Non-Refundable Pet Fee "
                             "Per Stay: $75.00 Maximum Pet Weight: 40.0lbs")
    assert result["extraction"]["pet_fee"] == 7500
    assert "pet_fee" not in result["withheld"]


# --------------------------------------------------------------------------- #
# The measured corpus, dry run and queue.
# --------------------------------------------------------------------------- #

def test_the_corpus_covers_every_required_group():
    doc = corpus_report()
    groups = doc["corpus_by_group"]
    assert groups["hilton"] == 11
    assert groups["marriott_control"] == 3
    assert groups["generic_control"] == 10


def test_every_hilton_tiered_understatement_is_corrected():
    recheck = corpus_report()["hilton_recheck"]
    assert recheck["tiered_understatement_corrected"] == 5
    assert recheck["false_preemption_corrected"] == 1
    for row in recheck["rows"]:
        if row["asserted_fee_before"] and row["tiered"]:
            assert not row["asserts_fee_now"], row["canonical_name"]


def test_no_hilton_record_gained_a_fee_it_did_not_have():
    """The fix only ever ADDS withholding; it must never invent an assertion."""
    for row in corpus_report()["hilton_recheck"]["rows"]:
        if not row["asserted_fee_before"]:
            assert not row["asserts_fee_now"], row["canonical_name"]


def test_the_dry_run_measured_the_whole_corpus_read_only():
    doc = dry()
    assert doc["blocks_scanned"] >= 190
    assert doc["blocks_withholding_fee_for_schema"] > 0
    assert set(doc["by_cause"]) <= {"TIERED", "UNREPRESENTED_COMPONENT", "OTHER"}


def test_the_queue_separates_store_rows_from_hilton_rows():
    doc = queue()
    assert doc["count"] == doc["in_observation_store"] + doc["outside_observation_store"]
    assert doc["in_observation_store"] > 0
    assert doc["applied"] is False


def test_no_published_record_is_affected():
    """The reassurance that matters: published is 0, so nothing live moved."""
    assert queue()["published_affected"] == 0
    store = json.loads(
        (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
         / "milwaukee-wi_policy_proposals_001.json").read_text(
            encoding="utf-8-sig"))
    assert sum(1 for i in store["items"] if i.get("published")) == 0


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_provider_routing_is_unchanged():
    # policy_locator.py left this freeze in 032, which added an optional
    # recovery block to the record. The contract version and replay
    # semantics are unchanged and are pinned by 021/022/023.
    for brand, provider in (("HILTON", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("CHOICE", PROVIDERS.FIRECRAWL),
                            ("WYNDHAM", PROVIDERS.FIRECRAWL),
                            ("IHG", PROVIDERS.FIRECRAWL)):
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.com/x").provider == provider
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 024" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()

def test_the_canonical_locator_contract_is_untouched():
    assert PL.CONTRACT == "ptf-policy-locator/1.0"


def test_this_work_order_declared_no_store_integration():
    """024 measured semantics and applied nothing.

    The store was reconciled afterwards by
    PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025. What remains true of 024
    is that its own queue was never applied.
    """
    assert queue()["applied"] is False
    assert corpus_report()["observations_updated"] is False


def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found


def test_nothing_was_published():
    doc = corpus_report()
    assert doc["published"] is False
    assert doc["authority_written"] is False
    assert doc["observations_updated"] is False
    assert doc["routes_changed"] is False
