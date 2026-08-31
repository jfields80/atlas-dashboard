"""PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 -- the guarantees, tested.

Same split as the Marriott pilot's suite. STRUCTURAL tests need no network and
no artifacts and run everywhere; ARTIFACT tests read the committed reports and
the gitignored raw tree, and SKIP when the raw tree is absent rather than
failing a fresh clone.

The additions this pilot needs over the previous one are the ones its extra
freedom creates: a US exit pin that must be verified rather than requested, a
sample that must be exactly thirty in exactly six buckets with two brands
excluded on cost grounds, and an identity gate that has to hold when the brand
puts no property code in its URLs.
"""

from __future__ import annotations

import asyncio
import collections
import inspect
import json
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import client
from scripts.pettripfinder.brightdata import corpus as CORPUS
from scripts.pettripfinder.brightdata import cross_brand_capture as CBC
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as PILOT
from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import outcomes as O
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.brightdata import policy_surface as PS
from scripts.pettripfinder.brightdata import publication_grade as PG
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EV
from scripts.pettripfinder.policy import policy_observation as PO

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CREDENTIAL_SHAPES = ("brd-customer", "superproxy", "wss://",
                      "BRIGHTDATA_BROWSER_AUTH=")


# --------------------------------------------------------------------------- #
# The sample.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def sample():
    return PILOT.build_sample()


def test_the_pilot_is_exactly_thirty_properties(sample):
    assert PILOT.PILOT_SIZE == 30
    assert len(sample) == 30
    assert len({r.source_url.rstrip("/").lower() for r in sample}) == 30


def test_the_brand_distribution_is_five_each(sample):
    counts = collections.Counter(r.bucket for r in sample)
    assert set(counts) == set(CORPUS.BUCKETS)
    assert all(counts[b] == PILOT.PER_BUCKET for b in CORPUS.BUCKETS)
    assert CORPUS.NAMED_BUCKETS == ("MARRIOTT", "HILTON", "IHG", "CHOICE",
                                    "WYNDHAM")


def test_hyatt_and_best_western_are_excluded(sample):
    """Premium domains under the current plan. A budget decision, enforced."""
    assert CORPUS.EXCLUDED_BRANDS == frozenset({"HYATT", "BEST_WESTERN"})
    for record in sample:
        assert record.brand not in CORPUS.EXCLUDED_BRANDS
        assert "hyatt.com" not in record.source_url.lower()
        assert "bestwestern.com" not in record.source_url.lower()
    assert not [r for r in CORPUS.load_corpus()
                if r.brand in CORPUS.EXCLUDED_BRANDS]


def test_the_variety_floor_is_met(sample):
    coverage = CORPUS.coverage(sample)
    for category, minimum in PILOT.SAMPLE_MINIMUMS.items():
        assert coverage[category] >= minimum, (category, coverage[category])
    assert coverage[CORPUS.CAT_NO_PETS] >= 5
    assert coverage[CORPUS.CAT_STRUCTURED_POSITIVE] >= 5
    assert coverage[CORPUS.CAT_CONTRADICTION] >= 3
    assert coverage[CORPUS.CAT_DYNAMIC] >= 3
    assert coverage[CORPUS.CAT_DIFFICULT] >= 3


def test_the_sample_is_deterministic():
    first = [r.identity_key for r in PILOT.build_sample()]
    second = [r.identity_key for r in PILOT.build_sample()]
    assert first == second


def test_the_mixed_bucket_spreads_across_sub_brands(sample):
    mixed = [r for r in sample if r.bucket == CORPUS.MIXED_BUCKET]
    brands = {r.brand if not r.brand.startswith(CORPUS.INDEPENDENT_PREFIX)
              else CORPUS.INDEPENDENT_PREFIX for r in mixed}
    assert len(brands) == len(mixed), brands


def test_build_sample_refuses_a_short_bucket(monkeypatch):
    monkeypatch.setattr(PILOT, "PER_BUCKET", 500)
    with pytest.raises((PILOT.PilotError, CORPUS.CorpusError)):
        PILOT.build_sample()


def test_every_benchmark_record_has_a_first_party_url(sample):
    for record in sample:
        assert record.source_url.startswith("https://")
        assert record.quotes or record.origin == "policy_record"


# --------------------------------------------------------------------------- #
# US exit geography.
# --------------------------------------------------------------------------- #

def test_country_pinning_rewrites_only_the_username():
    pinned = client.pin_country("brd-customer-abc-zone-z:secret@host:9222", "us")
    assert pinned == "brd-customer-abc-zone-z-country-us:secret@host:9222"
    assert pinned.endswith(":secret@host:9222")


def test_country_pinning_replaces_rather_than_stacks():
    once = client.pin_country("brd-customer-a-zone-z-country-de:p@h:1", "us")
    twice = client.pin_country(once, "us")
    assert once == twice
    assert once.count("-country-") == 1


def test_country_pinning_refuses_a_bad_code():
    with pytest.raises(client.BrightDataCredentialError):
        client.pin_country("brd-customer-a-zone-z:p@h:1", "united-states")


def test_the_endpoint_is_pinned_by_default(monkeypatch):
    monkeypatch.setenv(client.AUTH_ENV, "brd-customer-a-zone-z:p@h:9222")
    assert client.DEFAULT_COUNTRY == "us"
    assert "-country-us:" in client.browser_endpoint()
    assert "-country-us:" not in client.browser_endpoint(country=None)


def test_the_cross_brand_capture_uses_the_pinned_endpoint():
    source = inspect.getsource(CBC.run_attempt)
    assert "client.DEFAULT_COUNTRY" in source
    assert "US-pinned" in source


def test_a_probe_that_cannot_read_a_country_is_a_failure():
    """Geography that cannot be established may not be assumed."""
    probe = BC.GeoProbe(ok=False, country="<none>", expected="us",
                        detail="only 0 of 6 sessions reported")
    assert not probe.ok
    assert probe.to_dict()["probe_url"] == client.GEO_PROBE_URL


def test_an_aborted_run_reports_geo_failure_and_no_properties():
    summary_input = {"run_id": "x", "us_geo_pin": {"ok": False}, "properties": []}
    summary = PILOT.summarize(summary_input)
    assert summary["us_geo_pin"] == "FAIL"
    assert summary["total"] == 0


# --------------------------------------------------------------------------- #
# The retry model is unchanged.
# --------------------------------------------------------------------------- #

def _record(attempt, outcome):
    return BC.AttemptRecord(attempt=attempt, outcome=outcome,
                            started_at="2026-08-18T00:00:00+00:00",
                            ended_at="2026-08-18T00:00:10+00:00",
                            elapsed_seconds=10.0,
                            requested_url="https://www.hilton.com/x")


def _target():
    return BC.CaptureTarget(slug="t", hotel="Test Hotel",
                            requested_url="https://www.hilton.com/x",
                            property_code="", market_id="m",
                            normalized_name="test hotel")


def _drive(monkeypatch, scripted, tmp_path):
    calls = {"n": 0}

    async def fake_attempt(target, attempt, *, run_dir, brand):
        calls["n"] += 1
        outcome = scripted[attempt - 1]
        payload = {"reading": None, "surface": None, "artifacts": {}} \
            if outcome == O.VALID else None
        return _record(attempt, outcome), payload

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(CBC, "run_attempt", fake_attempt)
    monkeypatch.setattr(CBC.asyncio, "sleep", no_sleep)
    records, payload = asyncio.run(
        CBC.capture_property(_target(), run_dir=tmp_path, brand="HILTON"))
    return records, payload, calls["n"]


def test_at_most_three_attempts(monkeypatch, tmp_path):
    records, payload, calls = _drive(
        monkeypatch, [O.ACCESS_DENIED, O.ACCESS_DENIED, O.UNHYDRATED], tmp_path)
    assert BC.MAX_ATTEMPTS == 3 and calls == 3 and len(records) == 3
    assert payload is None


def test_a_failed_attempt_does_not_terminate_the_batch(monkeypatch, tmp_path):
    records, payload, calls = _drive(
        monkeypatch, [O.ACCESS_DENIED, O.UNEXPECTED_PAGE, O.VALID], tmp_path)
    assert calls == 3
    assert [r.outcome for r in records][-1] == O.VALID
    assert payload is not None


def test_retrying_stops_at_the_first_valid(monkeypatch, tmp_path):
    _, _, calls = _drive(monkeypatch, [O.VALID, O.VALID, O.VALID], tmp_path)
    assert calls == 1


def test_every_attempt_carries_exactly_one_outcome_from_the_closed_set():
    assert len(O.OUTCOMES) == 9
    for outcome in O.OUTCOMES:
        assert O.may_bear_evidence(outcome) is (outcome == O.VALID)


# --------------------------------------------------------------------------- #
# The health and identity gates, generically.
# --------------------------------------------------------------------------- #

_HILTON_URL = ("https://www.hilton.com/en/hotels/daycvhx-hampton-dayton-south/"
               "hotel-info/")


def test_access_denied_fails_on_any_brand():
    outcome = PS.page_health(
        title="Access Denied", body_text="Access Denied " + "x" * 4000,
        final_url=_HILTON_URL, expected_url=_HILTON_URL,
        expected_property_code="daycvhx", brand="HILTON")
    assert outcome == O.ACCESS_DENIED
    assert not O.may_bear_evidence(outcome)


def test_a_blank_page_fails_on_any_brand():
    outcome = PS.page_health(title="", body_text="  ", final_url=_HILTON_URL,
                             expected_url=_HILTON_URL,
                             expected_property_code="daycvhx", brand="HILTON")
    assert outcome == O.BLANK_PAGE


def test_an_unhydrated_shell_fails_on_any_brand():
    outcome = PS.page_health(title="Hampton Inn Dayton South",
                             body_text="Hampton Inn", final_url=_HILTON_URL,
                             expected_url=_HILTON_URL,
                             expected_property_code="daycvhx", brand="HILTON")
    assert outcome == O.UNHYDRATED


def test_a_generic_brand_page_never_passes():
    """The failure that cost the previous pilot a property, on every brand."""
    for brand, home, expected in (
            ("MARRIOTT", "https://www.marriott.com/default.mi",
             "https://www.marriott.com/en-us/hotels/dtwad-x/overview/"),
            ("HILTON", "https://www.hilton.com/en/", _HILTON_URL),
            ("IHG", "https://www.ihg.com/hotels/us/en/reservation",
             "https://www.ihg.com/holidayinn/hotels/us/en/dayton/dayoh/hoteldetail"),
            ("CHOICE", "https://www.choicehotels.com/",
             "https://www.choicehotels.com/ohio/canton/comfort-inn-hotels/oh123"),
    ):
        outcome = PS.page_health(
            title="Book direct", body_text="y" * 6000, final_url=home,
            expected_url=expected,
            expected_property_code=PS.property_code(expected, brand),
            brand=brand)
        assert outcome == O.UNEXPECTED_PAGE, brand


def test_a_foreign_locale_generic_page_never_passes():
    """marriott.com/es/default.mi -- what an unpinned exit actually produced."""
    expected = "https://www.marriott.com/en-us/hotels/dtwli-detroit-marriott-livonia/overview/"
    outcome = PS.page_health(
        title="Hoteles Marriott Bonvoy", body_text="z" * 5000,
        final_url="https://www.marriott.com/es/default.mi",
        expected_url=expected, expected_property_code="dtwli", brand="MARRIOTT")
    assert outcome == O.UNEXPECTED_PAGE


def test_a_brand_with_no_property_code_still_rejects_its_homepage():
    """Independents have no code, so the binding is the property's own path."""
    expected = "https://www.omnihotels.com/hotels/pittsburgh-william-penn"
    assert PS.property_code(expected, "INDEP:www.omnihotels.com") == ""
    assert PS.page_health(
        title="Omni Hotels", body_text="q" * 6000,
        final_url="https://www.omnihotels.com/", expected_url=expected,
        expected_property_code="", brand="INDEP") == O.UNEXPECTED_PAGE
    assert PS.page_health(
        title="Omni William Penn", body_text="q" * 6000,
        final_url=expected, expected_url=expected,
        expected_property_code="", brand="INDEP") is None


def test_a_sibling_property_never_passes_identity():
    signals = MS.IdentitySignals(name_on_page="Hampton Inn Springfield",
                                 property_code_on_page="dayspx",
                                 canonical_url="https://www.hilton.com/en/hotels/"
                                               "dayspx-hampton-springfield/",
                                 jsonld_present=True)
    assessment = PS.assess_identity(
        signals, expected_name="Hampton Inn Dayton/Huber Heights",
        expected_property_code="dayhhhx", expected_url=_HILTON_URL)
    assert not assessment.confirmed
    assert "property_code" in assessment.signals_conflicting


def test_a_partial_name_match_still_needs_a_second_signal():
    signals = MS.IdentitySignals(name_on_page="Hampton Inn by Hilton Dayton South",
                                 jsonld_present=True)
    assessment = PS.assess_identity(
        signals, expected_name="Hampton Inn Dayton South",
        expected_property_code="", expected_url=_HILTON_URL)
    assert not assessment.confirmed


def test_path_identity_ignores_a_one_segment_path():
    assert PS.path_identity("https://www.hilton.com/") == ""
    assert PS.path_identity("https://www.hilton.com/en/") == ""
    assert PS.path_identity(_HILTON_URL).startswith("/en/hotels/")


# --------------------------------------------------------------------------- #
# Bounded extraction, generically.
# --------------------------------------------------------------------------- #

def test_the_signal_phrases_never_match_a_gym():
    noise = ("Fitness center with cardiovascular and weight equipment. "
             "Pet grooming nearby.").lower()
    assert not [p for p in PS.SIGNAL_PHRASES if p in noise]
    reading = PR.parse(noise)
    assert reading.pets_allowed is None
    assert not PR.to_extraction(reading, location="b").extraction


def test_signal_phrases_all_name_pets_and_an_act():
    for phrase in PS.SIGNAL_PHRASES:
        assert "pet" in phrase or "animal" in phrase or "dog" in phrase, phrase
        assert phrase != "pet" and phrase != "pets"


def test_a_container_larger_than_the_cap_is_not_a_policy_block():
    assert PS.MAX_BLOCK_CHARS <= 1500
    assert "maxBlock" in PS._LOCATE_SCRIPT


@pytest.mark.parametrize("block,expected", [
    ("Pet Policy Pets Not Allowed", False),
    ("Pets Allowed: No", False),
    ("Pets: Pets are welcome. $75 non-refundable fee per stay.", True),
    ("We welcome pets! 2 pets per room, up to 75 lbs.", True),
    ("One well-behaved family pet per room is welcome.", True),
])
def test_pets_allowed_reads_across_brand_wordings(block, expected):
    assert PR.parse(block).pets_allowed is expected


def test_a_scoped_charge_records_the_scope_the_source_stated():
    result = PR.to_extraction(
        PR.parse("Pets are welcome. $25 per pet, per night."), location="b")
    assert result.extraction["pet_fee"] == 2500
    assert result.extraction["fee_basis"] == enums.BASIS_PER_NIGHT
    assert result.extraction["fee_scope"] == enums.SCOPE_PER_PET


def test_an_unscoped_charge_leaves_scope_absent():
    result = PR.to_extraction(
        PR.parse("Pets welcome. Non-Refundable Pet Fee Per Stay: $150.00"),
        location="b")
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert "fee_scope" not in result.extraction
    assert any("fee_scope" in note for note in result.non_inferences)


def test_no_unsupported_inference_across_brands():
    for block in ("Pets welcome. Maximum Pet Weight: 50.0lbs",
                  "Pets are welcome, up to 75 lbs.",
                  "Pet friendly. 50 lbs or less."):
        result = PR.to_extraction(PR.parse(block), location="b")
        limit = result.extraction.get("weight_limit") or {}
        assert "operator" not in limit
        assert "scope" not in limit
        assert "species_allowed" not in result.extraction
        assert any("operator" in note for note in result.non_inferences)


def test_a_contradiction_survives_the_generic_reader():
    block = ("Pets Welcome Pet fee $20/day with $100/stay nonrefundable clean "
             "fee Non-Refundable Pet Fee Per Stay: $100.00 "
             "Non-Refundable Pet Fee Per Night: $20.00")
    reading = PR.parse(block)
    result = PR.to_extraction(reading, location="b")
    assert result.extraction["pet_fee"] == 2000
    assert "fee_basis" not in result.extraction
    assert result.withheld["fee_basis"] == enums.SOURCE_CONTRADICTORY
    assert result.extraction["cleaning_fee"] == 10000


def test_the_more_specific_statement_governs():
    """'Pets Allowed: No' contains 'Pets Allowed' and is not a contradiction."""
    reading = PR.parse("Pets Allowed: No")
    assert reading.pets_allowed is False
    assert not reading.contradictions


def test_generic_extraction_stays_inside_the_frozen_vocabulary():
    for block in ("Pets Allowed: Yes. $25 per pet, per night. Dogs Only.",
                  "Pet Policy Pets Not Allowed",
                  "We welcome pets! 2 pets per room, up to 75 lbs."):
        result = PR.to_extraction(PR.parse(block), location="b")
        assert set(result.extraction) <= PO.EXTRACTION_FIELDS
        assert {f["code"] for f in result.flags} <= PO.FLAG_CODES
        assert set(result.withheld.values()) <= set(enums.WITHHOLDING_REASONS)


def test_every_generic_quote_is_contiguous_in_its_block():
    blocks = (
        "Pets Allowed: Yes. $25 per pet, per night. Maximum 2 pets per room. "
        "Dogs Only. 50 lbs or less.",
        "Pets: Pets are welcome. $75 non-refundable fee per stay. Maximum 2 "
        "pets per room, up to 75 lbs each. Service animals are welcome.",
    )
    for block in blocks:
        result = PR.to_extraction(PR.parse(block), location="b")
        for item in result.evidence:
            assert EV.quote_is_contiguous(item["quote"], block), item


# --------------------------------------------------------------------------- #
# The benchmark cannot reach the capture.
# --------------------------------------------------------------------------- #

def test_the_capture_path_cannot_import_the_benchmark():
    for module in (CBC, PS, PR, MS, BC, PG, client):
        source = inspect.getsource(module)
        assert "cross_brand_pilot_002" not in source, module.__name__
        assert "import corpus" not in source, module.__name__
        assert " corpus as" not in source, module.__name__


def test_a_capture_target_has_nowhere_to_put_a_policy_value():
    fields = set(BC.CaptureTarget.__dataclass_fields__)
    assert not (fields & {"facts", "quotes", "pets_allowed", "pet_fee",
                          "withheld_fields", "categories", "benchmark"})


def test_target_for_carries_inputs_only(sample):
    for record in sample[:6]:
        target = PILOT.target_for(record)
        rendered = json.dumps(target.hotel_ref())
        assert "pets_allowed" not in rendered
        assert str(record.facts.get("pet_fee") or "") not in rendered or \
            not record.facts.get("pet_fee")


def test_a_missing_capture_field_is_reported_not_filled(sample):
    record = next(r for r in sample if (r.facts or {}).get("pet_fee"))
    comparison = PILOT.compare(record, extraction={"pets_allowed": True},
                               withheld={}, block_text="Pets Welcome")
    verdicts = {k: v["verdict"] for k, v in comparison["fields"].items()}
    assert PILOT.CAPTURE_ABSENT in verdicts.values() or \
        PILOT.NOT_COMPARABLE in verdicts.values()
    assert comparison["fields"]["pets_allowed"]["captured"] is True


def test_a_withheld_benchmark_field_demands_absence():
    """Producing a value where the corpus withheld one is a MISMATCH."""
    record = CORPUS.BenchmarkRecord(
        identity_key="k", name="Test", market_id="m", brand="MARRIOTT",
        bucket="MARRIOTT", source_url="https://www.marriott.com/x",
        pets_allowed=True, facts={"pets_allowed": True},
        quotes=("Pets Welcome",),
        withheld_fields={"pet_fee": "CEILING != PRICE"},
        service_animal_statement="", categories=frozenset(),
        origin="policy_record")
    kept = PILOT.compare(record, extraction={"pets_allowed": True},
                         withheld={}, block_text="Pets Welcome")
    assert kept["fields"]["pet_fee_minor"]["verdict"] == PILOT.MATCH
    assert kept["contradiction_preserved"] is True

    resolved = PILOT.compare(record,
                             extraction={"pets_allowed": True, "pet_fee": 2500},
                             withheld={}, block_text="Pets Welcome")
    assert resolved["fields"]["pet_fee_minor"]["verdict"] == PILOT.MISMATCH
    assert resolved["contradiction_preserved"] is False


def test_a_tiered_benchmark_is_not_compared_against_a_flat_fee():
    record = CORPUS.BenchmarkRecord(
        identity_key="k", name="Test", market_id="m", brand="IHG",
        bucket="IHG", source_url="https://www.ihg.com/x", pets_allowed=True,
        facts={"pets_allowed": True,
               "fee_tiers": [{"amount_cents": 7500}, {"amount_cents": 15000}]},
        quotes=(), withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="policy_record")
    comparison = PILOT.compare(record,
                               extraction={"pets_allowed": True, "pet_fee": 7500},
                               withheld={}, block_text="")
    assert comparison["fields"]["pet_fee_minor"]["verdict"] == PILOT.NOT_COMPARABLE


# --------------------------------------------------------------------------- #
# Failure states never become evidence.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("outcome", [o for o in O.OUTCOMES if o != O.VALID])
def test_no_failure_state_reaches_a_candidate(outcome):
    record = _record(1, outcome)
    assert PILOT.disposition_for(record, {"extraction": {"pets_allowed": False}},
                                 "POLICY_NEGATIVE_CONFIRMED") == PILOT.HOLD
    assert PILOT.disposition_for(record, {"extraction": {"pets_allowed": True}},
                                 "POLICY_CONFIRMED") == PILOT.HOLD


def test_a_verified_no_pets_candidate_requires_a_captured_false():
    record = _record(1, O.VALID)
    assert PILOT.disposition_for(
        record, {"extraction": {"pets_allowed": False}},
        "POLICY_NEGATIVE_CONFIRMED") == PILOT.VERIFIED_NO_PETS_CANDIDATE
    assert PILOT.disposition_for(
        record, {"extraction": {}}, "POLICY_NEGATIVE_CONFIRMED") == PILOT.HOLD


# --------------------------------------------------------------------------- #
# Screenshots and hashes.
# --------------------------------------------------------------------------- #

def _png(tmp_path, name, ink):
    Image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    path = tmp_path / name
    image = Image.new("RGB", (4, 4), (255, 255, 255))
    if ink:
        image.putpixel((1, 1), (0, 0, 0))
    image.save(path)
    return path


def test_a_blank_crop_is_still_refused(tmp_path):
    assert BC.image_is_blank(_png(tmp_path, "flat.png", False)) is True
    assert BC.image_is_blank(_png(tmp_path, "ink.png", True)) is False


def test_hashes_rederive_from_bytes(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("policy", encoding="utf-8")
    assert _SHA256_RE.match(BC.sha256_file(path))
    assert BC.sha256_file(path) == BC.sha256_file(path)


def test_the_evidence_contract_is_used_not_changed():
    # PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029 carried Detroit onto this
    # lineage, and with it the text_extract artifact kind that founder
    # decision B-003-1 registered in Detroit order 004. 161 of Detroit's
    # committed evidence entries cite it, so the vocabulary GROWS here as
    # a committed change. What this test is actually about -- that
    # IMPORTING a capture package must not mutate a frozen vocabulary at
    # runtime -- is unchanged and still asserted.
    assert enums.ARTIFACT_KINDS == ("rendered_html", "operator_screenshot",
                                    "pdf", "text_extract")
    assert PO.CAPTURE_METHODS == ("deterministic_fetch", "browser_assisted",
                                  "human_manual", "phone_contact")
    assert EV.PUBLICATION_GRADE_REQUIRED == (
        "evidence_ref", "field", "quote", "source_url", "source_grade",
        "artifact_class", "artifact_sha256", "artifact_kind", "captured_at")
    codes = {g.code for g in PG.detect_gaps()}
    assert "GAP-01-NO-MACHINE-SCREENSHOT-KIND" in codes
    assert "GAP-02-NO-MANAGED-BROWSER-CAPTURE-METHOD" in codes
    assert "GAP-03-NO-CAPTURE-ENGINE-BINDING" in codes


# --------------------------------------------------------------------------- #
# Authority is frozen.
# --------------------------------------------------------------------------- #

def test_the_corpus_is_read_only():
    source = inspect.getsource(CORPUS)
    assert "write_text" not in source
    assert "json.dump" not in source
    assert "READ ONLY" in source


def test_the_pilot_writes_only_to_the_raw_tree_and_reports():
    assert PILOT.RAW_ROOT.parts[-4:] == ("worker_runs", "pettripfinder",
                                         PILOT.PILOT_ID, "raw")
    for path in (PILOT.SUMMARY_REPORT, PILOT.PROPERTY_REPORT,
                 PILOT.BRAND_REPORT, PILOT.SAMPLE_REPORT):
        assert path.parent == PILOT.REPORT_DIR


def test_nothing_promotes_or_publishes():
    for module in (CBC, PS, PR, CORPUS, PILOT):
        source = inspect.getsource(module)
        for forbidden in ("promote_", "publication_guard", "apply_decisions",
                          "PUBLISHED_PET_FRIENDLY"):
            assert forbidden not in source, (module.__name__, forbidden)


# --------------------------------------------------------------------------- #
# Committed outputs, once a run has produced them.
# --------------------------------------------------------------------------- #

def _load(path):
    if not path.exists():
        pytest.skip("%s has not been produced by a run yet" % path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_reports_carry_no_credential():
    for path in (PILOT.SUMMARY_REPORT, PILOT.PROPERTY_REPORT,
                 PILOT.BRAND_REPORT, PILOT.SAMPLE_REPORT):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert not client.contains_credential(text), path.name
        for shape in _CREDENTIAL_SHAPES:
            assert shape not in text, (path.name, shape)


def test_committed_summary_freezes_authority():
    summary = _load(PILOT.SUMMARY_REPORT)
    for key in ("policy_authority_changed", "exclusions_changed",
                "seed_changed", "approvals_changed", "partition_changed",
                "routing_authority_changed", "promotion_performed"):
        assert summary[key] is False, key
    assert summary["total"] == PILOT.PILOT_SIZE
    assert summary["us_geo_pin"] == "PASS"
    assert summary["false_verified_no_pets"] == 0


def test_committed_properties_are_thirty_in_six_buckets():
    report = _load(PILOT.PROPERTY_REPORT)
    properties = report["properties"]
    assert len(properties) == PILOT.PILOT_SIZE
    counts = collections.Counter(p["bucket"] for p in properties)
    assert all(counts[b] == PILOT.PER_BUCKET for b in CORPUS.BUCKETS)
    for prop in properties:
        assert len(prop["attempts"]) <= BC.MAX_ATTEMPTS
        for attempt in prop["attempts"]:
            assert attempt["outcome"] in O.OUTCOMES
            assert attempt["may_bear_evidence"] is (attempt["outcome"] == O.VALID)
        if not prop.get("successful_attempt"):
            assert prop["disposition"] == PILOT.CLAUDE_FALLBACK_REQUIRED
            assert "artifacts" not in prop


def test_committed_quotes_are_contiguous_in_the_committed_block():
    report = _load(PILOT.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        block = prop["policy_block_quote"]
        for item in prop["observation"]["evidence"]:
            assert EV.quote_is_contiguous(item["quote"], block), prop["slug"]


def test_committed_observations_validate_against_the_frozen_contract():
    report = _load(PILOT.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        PO.validate_observation(prop["observation"])
        assert set(prop["observation"]["extraction"]) <= PO.EXTRACTION_FIELDS


def test_committed_artifacts_hash_and_are_not_blank():
    report = _load(PILOT.PROPERTY_REPORT)
    checked = 0
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        files = prop["artifacts"]["files"]
        assert "rendered.html" in files and "page-text.txt" in files
        for name, entry in files.items():
            if not isinstance(entry, dict) or "sha256" not in entry:
                continue
            assert _SHA256_RE.match(entry["sha256"]), (prop["slug"], name)
            path = Path(entry["path"])
            if not path.exists():
                continue
            assert BC.sha256_file(path) == entry["sha256"], path
            if name.endswith(".png"):
                assert BC.image_is_blank(path) is not True, path
            checked += 1
    if checked == 0:
        pytest.skip("the gitignored raw artifact tree is not present here")


def test_no_false_verified_no_pets_in_the_committed_run():
    report = _load(PILOT.PROPERTY_REPORT)
    for prop in report["properties"]:
        if prop.get("disposition") != PILOT.VERIFIED_NO_PETS_CANDIDATE:
            continue
        extraction = prop["observation"]["extraction"]
        assert extraction.get("pets_allowed") is False, prop["slug"]
        block = prop["policy_block_quote"].lower()
        assert "not allowed" in block or "no pets" in block \
            or "not permitted" in block, prop["slug"]


# --------------------------------------------------------------------------- #
# A price is only a pet fee if the source says so.
# --------------------------------------------------------------------------- #

_CHOICE_ROOM_CARD = (
    "7 1 King Bed, 1 Bedroom Suite, Sofabed 4 Guests No Smoking No Pets "
    "Allowed 1 Bedroom Suite Sofa Bed Living Room No Pets Allowed Only "
    "service animals are permitted, free of charge. Flat Screen TV Desk Room "
    "Details Strikethrough Rate: $172 Discounted rate: $160 USD /night")


def test_a_room_rate_never_becomes_a_pet_fee():
    """A guest-room card carries a nightly price and the words 'No Pets'.

    Without a pet-context requirement the reader published the ROOM RATE as
    pet_fee $160 per_night against a Choice property.
    """
    reading = PR.parse(_CHOICE_ROOM_CARD)
    result = PR.to_extraction(reading, location="b")
    assert "pet_fee" not in result.extraction
    assert "fee_basis" not in result.extraction
    assert any("no pet wording" in note for note in reading.parser_notes)


def test_the_ignored_amount_is_reported_not_silently_dropped():
    reading = PR.parse(_CHOICE_ROOM_CARD)
    assert reading.parser_notes
    assert "$160" in " ".join(reading.parser_notes)


def test_a_labelled_pet_fee_still_reads():
    result = PR.to_extraction(
        PR.parse("Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00"),
        location="b")
    assert result.extraction["pet_fee"] == 15000


def test_pet_context_is_bounded():
    """Far enough for a real fee line, too narrow to cross a room card."""
    assert PR._PET_CONTEXT_CHARS <= 100
    near = "Pet fee is $25 per night."
    # Real filler, not whitespace: the reader collapses runs of spaces before
    # measuring, so padding with blanks would not put any distance between the
    # pet word and the price.
    far = ("Pets welcome. " + "Free parking and complimentary breakfast. " * 6
           + "Rate: $160 per night.")
    assert PR.to_extraction(PR.parse(near), location="b").extraction.get("pet_fee")
    assert "pet_fee" not in PR.to_extraction(PR.parse(far), location="b").extraction


# --------------------------------------------------------------------------- #
# A policy block is about pets.
# --------------------------------------------------------------------------- #

def test_the_locator_requires_a_block_to_be_about_pets():
    assert PS.MIN_PET_MENTIONS_LONG > PS.MIN_PET_MENTIONS_SHORT
    assert "minMentionsLong" in PS._LOCATE_SCRIPT
    assert "aboutPets(text)" in PS._LOCATE_SCRIPT


def test_a_long_block_with_a_single_pet_word_is_rejected():
    """The rule's real job: a page section that merely CONTAINS a pet word.

    Wyndham's amenity list is the boundary case and it is admitted on purpose
    -- it carries "Pet Friendly" and "Service Animals Welcome", which is a thin
    but genuine statement, and the alternative the locator reached for was a
    twenty-three-character fragment. What must never qualify is a long block
    whose entire pet content is one incidental mention.
    """
    lodging = ("Hotel Amenities 100% Smoke-Free Hotel 24-Hour Front Desk "
               "Banquet Facilities Coffee Maker Cribs Daily Housekeeping "
               "Dry Cleaning Early Check-in Event Planning Express Check-in "
               "Free Parking Free WiFi Hairdryer Luggage Hold Meeting Room "
               "Pool Outdoor RV Parking Safe Deposit Box Wedding Services "
               "Accessible Front Desk Accessible Guest Room Doorways "
               "Accessible Public Entrance Accessible Route Staff Trained")
    one_mention = lodging + " Pet Friendly"
    assert len(one_mention) > PS.LONG_BLOCK_CHARS
    hits = len(re.findall(r"pets?|animals?|dogs?|cats?", one_mention, re.I))
    assert hits == 1
    assert hits < PS.MIN_PET_MENTIONS_LONG

    two_mentions = one_mention + " Service Animals Welcome"
    hits = len(re.findall(r"pets?|animals?|dogs?|cats?", two_mentions, re.I))
    assert hits >= PS.MIN_PET_MENTIONS_LONG


def test_a_short_statement_qualifies_on_one_mention():
    short = "Pets are welcome."
    assert len(short) <= PS.LONG_BLOCK_CHARS
    assert PS.MIN_PET_MENTIONS_SHORT == 1


def test_a_real_policy_block_is_about_pets():
    block = ("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Max "
             "weight 75 lbs 2 pets max; dog or cat only")
    hits = len(re.findall(r"pets?|animals?|dogs?|cats?", block, re.I))
    floor = (PS.MIN_PET_MENTIONS_LONG if len(block) > PS.LONG_BLOCK_CHARS
             else PS.MIN_PET_MENTIONS_SHORT)
    assert hits >= floor


def test_the_locator_reads_displayed_text_not_concatenated_text():
    """textContent joined Hilton's table into 'Pets allowedYesDepositYes'."""
    assert "el.innerText" in PS._LOCATE_SCRIPT
    assert "const shown =" in PS._LOCATE_SCRIPT
    assert "shown(node)" in PS._LOCATE_SCRIPT


def test_brand_generic_wording_is_outranked_and_flagged():
    assert "GENERIC" in PS._LOCATE_SCRIPT
    reading = PR.parse("Pets are welcome at all our hotels; fees may apply")
    assert reading.brand_generic
    result = PR.to_extraction(reading, location="b")
    assert any(f["code"] == "FLAG_BRAND_GENERIC" for f in result.flags)
    assert {f["code"] for f in result.flags} <= PO.FLAG_CODES


def test_a_property_specific_block_is_not_flagged_generic():
    reading = PR.parse("Pets Welcome Non-Refundable Pet Fee Per Stay: $150.00")
    assert not reading.brand_generic


# --------------------------------------------------------------------------- #
# A service-animal quote is a sentence.
# --------------------------------------------------------------------------- #

def test_a_service_animal_quote_is_bounded():
    long_block = ("Pet Friendly " + "Free Parking Free WiFi Hairdryer " * 30
                  + "Service Animals Welcome Staff Trained")
    reading = PR.parse(long_block)
    quote = reading.service_animal_quote
    assert quote
    assert len(quote) <= PR._MAX_SERVICE_ANIMAL_CHARS + 60
    assert EV.quote_is_contiguous(quote, long_block)


def test_a_short_service_animal_sentence_is_kept_whole():
    block = ("Pets Welcome Pet fee $20/day excludes Service Animals "
             "Non-Refundable Pet Fee Per Stay: $100.00")
    reading = PR.parse(block)
    # The segmenter breaks at the acceptance statement and at each labelled
    # row, so the statement kept is the property's own prose sentence and not
    # the fee row beside it.
    assert reading.service_animal_quote == \
        "Pet fee $20/day excludes Service Animals"
    assert "Non-Refundable" not in reading.service_animal_quote
    assert EV.quote_is_contiguous(reading.service_animal_quote, block)


# --------------------------------------------------------------------------- #
# A house rule is not a refusal.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text,expected", [
    ("Pet Policy Pets Not Allowed", False),
    ("Pets Allowed: No", False),
    ("Pets are not allowed.", False),
    ("Pets are not allowed at this property.", False),
    ("No pets allowed", False),
    ("Pets Not Permitted", False),
    # House rules. Hotel Indigo Pittsburgh writes the first of these on a page
    # that also says "Pets are welcome"; reading it as a refusal made the
    # surface look self-contradictory and cost a whole capture.
    ("Pets are welcome. Pets are not allowed to be left alone in room.", True),
    ("Pets welcome. Pets are not allowed in the restaurant.", True),
    ("Pets welcome. Pets are not allowed on the furniture.", True),
])
def test_a_conditional_restriction_is_not_a_blanket_refusal(text, expected):
    assert PR.parse(text).pets_allowed is expected


def test_the_refusal_qualifier_reuses_the_frozen_alternation():
    """One definition of the refusal wordings, not two."""
    assert MS._PETS_REFUSED_RE.pattern in PR._PETS_REFUSED_RES[0].pattern
    assert PR._REFUSAL_QUALIFIER in PR._PETS_REFUSED_RES[0].pattern


def test_a_house_rule_alone_states_nothing():
    """Without an acceptance statement the surface is silent, not negative."""
    reading = PR.parse("Pets are not allowed to be left alone in the room.")
    assert reading.pets_allowed is None
    result = PR.to_extraction(reading, location="b")
    assert result.withheld.get("pets_allowed") == enums.SOURCE_SILENT


# --------------------------------------------------------------------------- #
# Re-derivation is pure.
# --------------------------------------------------------------------------- #

def test_rederivation_reads_only_persisted_text():
    """The capture is expensive and non-reproducible; the reading is not."""
    source = inspect.getsource(PILOT.rederive_journal)
    for network in ("connect_over_cdp", "async_playwright", "page.goto",
                    "capture_property", "probe_exit_country"):
        assert network not in source, network
    assert "PROGRESS_JOURNAL.write_text" in source
    assert "policy_block_quote" in source


def test_rederivation_preserves_the_attempt_record():
    """Artifacts, hashes and attempt metadata are untouched by a re-read."""
    source = inspect.getsource(PILOT.rederive_journal)
    assert 'entry.get("artifacts")' in source
    assert '"attempts"' not in source.split("entry.update")[-1]


# --------------------------------------------------------------------------- #
# Precision and recall are reported apart.
# --------------------------------------------------------------------------- #

def test_field_tallies_separate_wrong_from_not_found():
    properties = [
        {"benchmark_comparison": {"fields": {
            "pets_allowed": {"verdict": PILOT.MATCH},
            "pet_fee_minor": {"verdict": PILOT.CAPTURE_ABSENT},
            "fee_basis": {"verdict": PILOT.MISMATCH},
            "weight_limit_value": {"verdict": PILOT.BENCHMARK_SILENT},
            "pet_count_limit": {"verdict": PILOT.NOT_COMPARABLE},
        }}},
    ]
    tallies = PILOT.field_verdict_tallies(properties)
    critical = tallies["critical"]
    assert critical["match"] == 1
    assert critical["mismatch"] == 1
    assert critical["capture_absent"] == 1
    # Precision counts only what the reader produced; recall counts what it
    # could have produced.
    assert critical["precision_percent"] == 50.0
    assert round(critical["recall_percent"]) == 33


def test_a_reader_that_finds_nothing_has_no_precision():
    tallies = PILOT.field_verdict_tallies(
        [{"benchmark_comparison": {"fields": {
            "pets_allowed": {"verdict": PILOT.CAPTURE_ABSENT}}}}])
    assert tallies["critical"]["precision_percent"] is None
    assert tallies["critical"]["recall_percent"] == 0.0


# --------------------------------------------------------------------------- #
# Reconciliation.
# --------------------------------------------------------------------------- #

def test_reconciliation_is_read_only():
    from scripts.pettripfinder.brightdata import reconcile_002 as RECON
    source = inspect.getsource(RECON)
    for writer in ("write_text", "json.dump(", "unlink", "mkdir"):
        assert writer not in source, writer


def test_reconciliation_checks_cover_the_work_order():
    from scripts.pettripfinder.brightdata import reconcile_002 as RECON
    source = inspect.getsource(RECON)
    for claim in ("hash rederives", "contiguous", "flat colour",
                  "identity gate", "locale redirect", "unsupported inference",
                  "false VERIFIED_NO_PETS", "contradictions remain",
                  "no benchmark value reached a capture",
                  "Hyatt = 0 and Best Western = 0"):
        assert claim in source, claim


def test_the_committed_run_reconciles():
    """The whole reconciliation, against whatever is committed right now."""
    from scripts.pettripfinder.brightdata import reconcile_002 as RECON
    if not PILOT.PROPERTY_REPORT.exists():
        pytest.skip("no committed run to reconcile yet")
    if not PILOT.PROGRESS_JOURNAL.exists():
        pytest.skip("the gitignored journal is not present here")
    result = RECON.run()
    failed = [c for c in result["checks"] if not c["passed"]]
    assert not failed, [(c["name"], c["failures"]) for c in failed]
    assert result["journalled"] == PILOT.PILOT_SIZE
