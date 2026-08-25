"""PTF-BRIGHTDATA-MARRIOTT-PILOT-001 -- the guarantees, tested.

Two kinds of test live here and they are kept apart on purpose.

STRUCTURAL tests run everywhere and need no network and no artifacts. They
prove the things that must be true whether or not a run ever happened: the
pilot is five properties, an attempt has one of nine outcomes, only VALID may
carry evidence, and the benchmark cannot reach the capture path.

ARTIFACT tests read the committed reports and the gitignored raw tree. The raw
tree is absent from a fresh clone by construction, so those tests SKIP rather
than fail when it is not there -- and the report-only checks still run, so a
committed report that names an artifact with a bad hash shape, a stitched
quote, or a credential in it is caught in CI regardless.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import urllib.parse
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import client
from scripts.pettripfinder.brightdata import marriott_pilot_001 as PILOT
from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import outcomes as O
from scripts.pettripfinder.brightdata import publication_grade as PG
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EV
from scripts.pettripfinder.policy import policy_observation as PO

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: Credential shapes that must never appear in a committed file, tested
#: independently of whether this machine happens to hold the environment
#: variable. ``client.contains_credential`` covers the live secret; this covers
#: the shape, so the guard still bites in CI where the variable is unset.
_CREDENTIAL_SHAPES = ("brd-customer", "superproxy", "wss://", "BRIGHTDATA_BROWSER_AUTH=")


# --------------------------------------------------------------------------- #
# The pilot is five properties, and these five.
# --------------------------------------------------------------------------- #

def test_pilot_is_exactly_five_properties():
    assert PILOT.PILOT_SIZE == 5
    assert len(PILOT.TARGET_SPECS) == 5
    assert len(PILOT.build_targets()) == 5
    assert len(PILOT.BENCHMARK) == 5


def test_exact_hotel_urls():
    """The five URLs the work order named, character for character."""
    assert {url for _, _, url in PILOT.TARGET_SPECS} == {
        "https://www.marriott.com/en-us/hotels/"
        "dtwad-ac-hotel-ann-arbor-downtown/overview/",
        "https://www.marriott.com/en-us/hotels/"
        "dtwdc-courtyard-detroit-downtown/overview/",
        "https://www.marriott.com/en-us/hotels/"
        "dttdb-courtyard-detroit-dearborn/overview/",
        "https://www.marriott.com/en-us/hotels/"
        "dtwli-detroit-marriott-livonia/overview/",
        "https://www.marriott.com/en-us/hotels/"
        "dtwrm-detroit-metro-airport-marriott/overview/",
    }


def test_every_target_has_a_benchmark_and_a_property_code():
    for target in PILOT.build_targets():
        assert target.slug in PILOT.BENCHMARK
        assert target.property_code
        assert target.requested_url.startswith("https://www.marriott.com/")


def test_build_targets_refuses_to_widen(monkeypatch):
    """A five-property pilot that quietly ran forty is not what was authorised."""
    monkeypatch.setattr(PILOT, "TARGET_SPECS",
                        PILOT.TARGET_SPECS + PILOT.TARGET_SPECS[:1])
    with pytest.raises(PILOT.PilotError):
        PILOT.build_targets()


# --------------------------------------------------------------------------- #
# The retry harness.
# --------------------------------------------------------------------------- #

def _record(attempt: int, outcome: str) -> BC.AttemptRecord:
    return BC.AttemptRecord(attempt=attempt, outcome=outcome,
                            started_at="2026-08-18T00:00:00+00:00",
                            ended_at="2026-08-18T00:00:10+00:00",
                            elapsed_seconds=10.0,
                            requested_url="https://www.marriott.com/x")


def _target() -> BC.CaptureTarget:
    return BC.CaptureTarget(slug="t", hotel="Test Hotel",
                            requested_url="https://www.marriott.com/x",
                            property_code="dtwad", market_id="m",
                            normalized_name="test hotel")


def _drive(monkeypatch, scripted, tmp_path):
    """Run ``capture_property`` over a scripted list of outcomes."""
    calls = {"n": 0}

    async def fake_attempt(target, attempt, *, run_dir):
        calls["n"] += 1
        outcome = scripted[attempt - 1]
        payload = {"reading": None, "artifacts": {}, "locator_id": "x"} \
            if outcome == O.VALID else None
        return _record(attempt, outcome), payload

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(BC, "run_attempt", fake_attempt)
    monkeypatch.setattr(BC.asyncio, "sleep", no_sleep)
    records, payload = asyncio.run(
        BC.capture_property(_target(), run_dir=tmp_path))
    return records, payload, calls["n"]


def test_at_most_three_attempts(monkeypatch, tmp_path):
    records, payload, calls = _drive(
        monkeypatch, [O.ACCESS_DENIED, O.BLANK_PAGE, O.UNHYDRATED], tmp_path)
    assert BC.MAX_ATTEMPTS == 3
    assert calls == 3
    assert len(records) == 3
    assert payload is None


def test_retrying_stops_at_the_first_valid(monkeypatch, tmp_path):
    records, payload, calls = _drive(
        monkeypatch, [O.BLANK_PAGE, O.VALID, O.ACCESS_DENIED], tmp_path)
    assert calls == 2
    assert [r.outcome for r in records] == [O.BLANK_PAGE, O.VALID]
    assert payload is not None


def test_a_failed_attempt_does_not_terminate_the_batch(monkeypatch, tmp_path):
    """The proof's key behaviour: two bad sessions, then a good one."""
    records, payload, _ = _drive(
        monkeypatch, [O.NAVIGATION_FAILED, O.UNHYDRATED, O.VALID], tmp_path)
    assert [r.outcome for r in records] == [O.NAVIGATION_FAILED,
                                            O.UNHYDRATED, O.VALID]
    assert payload is not None


def test_run_attempt_never_raises_without_a_credential(monkeypatch, tmp_path):
    monkeypatch.delenv(client.AUTH_ENV, raising=False)
    record, payload = asyncio.run(
        BC.run_attempt(_target(), 1, run_dir=tmp_path))
    assert record.outcome == O.NAVIGATION_FAILED
    assert payload is None


# --------------------------------------------------------------------------- #
# A failure never becomes evidence.
# --------------------------------------------------------------------------- #

def test_only_valid_may_bear_evidence():
    assert O.EVIDENCE_BEARING_OUTCOMES == frozenset({O.VALID})
    for outcome in O.OUTCOMES:
        assert O.may_bear_evidence(outcome) is (outcome == O.VALID)


@pytest.mark.parametrize("outcome", [o for o in O.OUTCOMES if o != O.VALID])
def test_no_failure_state_reaches_a_candidate_disposition(outcome):
    record = _record(1, outcome)
    observation = {"extraction": {"pets_allowed": False}}
    assert PILOT.disposition_for(record, observation,
                                 "POLICY_NEGATIVE_CONFIRMED") == PILOT.HOLD
    observation = {"extraction": {"pets_allowed": True}}
    assert PILOT.disposition_for(record, observation,
                                 "POLICY_CONFIRMED") == PILOT.HOLD


def test_access_denied_is_detected_and_never_evidence():
    outcome = MS.page_health(
        title="Access Denied",
        body_text="Access Denied You don't have permission to access "
                  "this resource. " + "x" * 4000,
        final_url="https://www.marriott.com/en-us/hotels/dtwad-x/overview/",
        expected_property_code="dtwad")
    assert outcome == O.ACCESS_DENIED
    assert not O.may_bear_evidence(outcome)


def test_blank_page_is_detected_and_never_evidence():
    outcome = MS.page_health(
        title="", body_text="   ",
        final_url="https://www.marriott.com/en-us/hotels/dtwad-x/overview/",
        expected_property_code="dtwad")
    assert outcome == O.BLANK_PAGE
    assert not O.may_bear_evidence(outcome)


def test_unhydrated_shell_is_detected_and_never_evidence():
    """The observed Marriott failure: correct identity, empty body."""
    outcome = MS.page_health(
        title="AC Hotel Ann Arbor Downtown", body_text="AC Hotel Ann Arbor",
        final_url="https://www.marriott.com/en-us/hotels/"
                  "dtwad-ac-hotel-ann-arbor-downtown/overview/",
        expected_property_code="dtwad")
    assert outcome == O.UNHYDRATED
    assert not O.may_bear_evidence(outcome)


def test_a_generic_landing_page_is_unexpected_not_valid():
    outcome = MS.page_health(
        title="Marriott Bonvoy Hotels", body_text="x" * 5000,
        final_url="https://www.marriott.com/default.mi",
        expected_property_code="dtwad")
    assert outcome == O.UNEXPECTED_PAGE


def test_an_offsite_redirect_is_unexpected():
    outcome = MS.page_health(
        title="Book now", body_text="y" * 5000,
        final_url="https://booking.example.com/marriott/dtwad",
        expected_property_code="dtwad")
    assert outcome == O.UNEXPECTED_PAGE


def test_identity_mismatch_is_refused_even_with_a_matching_code():
    """A code that agrees with a name that does not is a conflict, not a pass."""
    signals = MS.IdentitySignals(name_on_page="Westin Southfield Detroit",
                                 postal_code="48034",
                                 property_code_on_page="dtwad",
                                 jsonld_present=True)
    assessment = MS.assess_identity(
        signals, expected_name="AC Hotel Ann Arbor Downtown",
        expected_property_code="dtwad", expected_postal_code="48104")
    assert not assessment.confirmed
    assert "name" in assessment.signals_conflicting


def test_identity_needs_more_than_a_name():
    """Name alone never confirms when a stronger signal exists and is absent."""
    signals = MS.IdentitySignals(name_on_page="AC Hotel Ann Arbor Downtown",
                                 jsonld_present=True)
    assessment = MS.assess_identity(
        signals, expected_name="AC Hotel Ann Arbor Downtown",
        expected_property_code="dtwad")
    assert not assessment.confirmed


# --------------------------------------------------------------------------- #
# Bounded extraction.
# --------------------------------------------------------------------------- #

_AC_BLOCK = ("Pet Policy Pets Welcome Pet Fee Per Stay $150 Maximum Pet Weight "
             "50lbs Maximum Number of Pets in Room 1 Non-Refundable Pet Fee "
             "Per Stay: $150.00 Maximum Pet Weight: 50.0lbs Maximum Number of "
             "Pets in Room: 1")

_DEARBORN_BLOCK = ("Pet Policy Pets Welcome Pet fee $20/day with $100/stay "
                   "nonrefundable clean fee excludes Service Animals "
                   "Non-Refundable Pet Fee Per Stay: $100.00 "
                   "Non-Refundable Pet Fee Per Night: $20.00 "
                   "Maximum Pet Weight: 35.0lbs "
                   "Maximum Number of Pets in Room: 2")


def test_the_keyword_sweep_regression_is_gone():
    """The proof captured a fitness-centre sentence as pet policy.

    Bounded extraction reads a CONTAINER, so page text outside it -- however
    many of the old keywords it contains -- is not in the reading at all.
    """
    noise = "Fitness center with cardiovascular and weight equipment"
    reading = MS.parse_policy_block(_AC_BLOCK)
    assert noise not in reading.block_text
    result = MS.to_extraction(reading, location="block")
    assert all(noise not in item["quote"] for item in result.evidence)


def test_ac_hotel_block_reads_exactly():
    reading = MS.parse_policy_block(_AC_BLOCK)
    result = MS.to_extraction(reading, location="block")
    assert result.extraction["pets_allowed"] is True
    assert result.extraction["pet_fee"] == 15000
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert result.extraction["weight_limit"] == {"value": 50.0, "unit": "lb"}
    assert result.extraction["pet_count_limit"] == 1
    assert result.extraction["pet_count_scope"] == enums.SCOPE_PER_ROOM


def test_contradiction_is_preserved_never_normalised():
    """per_day is not per_night, and this layer does not choose between them."""
    reading = MS.parse_policy_block(_DEARBORN_BLOCK)
    basis_conflicts = [c for c in reading.contradictions
                       if c["field"] == "fee_basis"]
    assert len(basis_conflicts) == 1
    assert set(basis_conflicts[0]["bases_stated"]) == {enums.BASIS_PER_DAY,
                                                       enums.BASIS_PER_NIGHT}
    assert basis_conflicts[0]["withholding_reason"] == enums.SOURCE_CONTRADICTORY
    # Both statements are kept, so a reviewer can see what disagreed.
    assert len(basis_conflicts[0]["quotes"]) == 2

    result = MS.to_extraction(reading, location="block")
    assert result.extraction["pet_fee"] == 2000
    assert "fee_basis" not in result.extraction
    assert result.withheld["fee_basis"] == enums.SOURCE_CONTRADICTORY
    assert any(f["code"] == "FLAG_AMBIGUOUS_BASIS" for f in result.flags)
    # The independently representable charge survives.
    assert result.extraction["cleaning_fee"] == 10000


def test_no_unsupported_inference():
    """Weight operator, weight scope, fee scope and species are never invented."""
    result = MS.to_extraction(MS.parse_policy_block(_AC_BLOCK),
                              location="block")
    assert "fee_scope" not in result.extraction
    assert "operator" not in result.extraction["weight_limit"]
    assert "scope" not in result.extraction["weight_limit"]
    assert "species_allowed" not in result.extraction
    assert "cats_allowed" not in result.extraction
    assert any("fee_scope" in n for n in result.non_inferences)
    assert any("operator" in n for n in result.non_inferences)


def test_named_species_are_read_and_only_named_species():
    reading = MS.parse_policy_block(
        "Pet Policy Pets Welcome Dogs Only Cats are not permitted "
        "Non-Refundable Pet Fee Per Stay: $150.00")
    result = MS.to_extraction(reading, location="block")
    assert result.extraction["species_allowed"] == ["dog"]
    assert result.extraction["cats_allowed"] is False


def test_pets_not_allowed_is_read_as_a_negative_fact():
    result = MS.to_extraction(MS.parse_policy_block("Pet Policy Pets Not Allowed"),
                              location="block")
    assert result.extraction["pets_allowed"] is False
    assert "pet_fee" not in result.extraction


def test_service_animal_text_does_not_swallow_the_fee_rows():
    """A sentence regex over an unpunctuated block took the whole surface."""
    reading = MS.parse_policy_block(_DEARBORN_BLOCK)
    assert reading.service_animal_quote == (
        "Pet fee $20/day with $100/stay nonrefundable clean fee excludes "
        "Service Animals")
    assert "Non-Refundable" not in reading.service_animal_quote


def test_every_quote_is_contiguous_in_its_block():
    for block in (_AC_BLOCK, _DEARBORN_BLOCK):
        reading = MS.parse_policy_block(block)
        result = MS.to_extraction(reading, location="block")
        for item in result.evidence:
            assert EV.quote_is_contiguous(item["quote"], block), item


def test_an_empty_container_is_not_a_reading():
    reading = MS.parse_policy_block("   ")
    assert not reading.found


# --------------------------------------------------------------------------- #
# The benchmark is never a capture source.
# --------------------------------------------------------------------------- #

def test_a_capture_target_has_nowhere_to_put_a_policy_value():
    fields = set(BC.CaptureTarget.__dataclass_fields__)
    forbidden = {"pets_allowed", "pet_fee", "pet_fee_minor", "fee_basis",
                 "weight_limit", "weight_limit_lb", "pet_count_limit",
                 "expected_phrases", "benchmark", "expected_disposition"}
    assert not (fields & forbidden)


def test_the_capture_path_cannot_reach_the_benchmark():
    """Structural, not conventional: the capture modules do not import the
    module the answers live in, so a benchmark value cannot leak into a
    capture even by mistake."""
    for module in (BC, MS, PG, client):
        source = inspect.getsource(module)
        assert "marriott_pilot_001" not in source, module.__name__
        assert "BENCHMARK" not in source, module.__name__


def test_the_benchmark_is_read_only_after_capture():
    """``compare_to_benchmark`` is the only reader, and it takes a finished
    extraction rather than producing one."""
    readers = [name for name, obj in vars(PILOT).items()
               if inspect.isfunction(obj) and "BENCHMARK["
               in inspect.getsource(obj)]
    assert sorted(readers) == ["compare_to_benchmark", "summarize"]


def test_a_missing_capture_field_is_reported_not_filled():
    comparison = PILOT.compare_to_benchmark(
        "ac-hotel-ann-arbor-downtown",
        extraction={"pets_allowed": True},          # no fee, no weight
        withheld={}, block_text="Pet Policy Pets Welcome")
    assert comparison["fields"]["pet_fee_minor"]["verdict"] == PILOT.CAPTURE_ABSENT
    assert comparison["fields"]["pet_fee_minor"]["captured"] is None
    assert not comparison["critical_field_exactness"]
    assert not comparison["policy_text_match"]


def test_a_normalised_contradiction_fails_the_dearborn_comparison():
    """If a capture reported either basis, the property must FAIL."""
    for basis in (enums.BASIS_PER_DAY, enums.BASIS_PER_NIGHT):
        comparison = PILOT.compare_to_benchmark(
            "courtyard-detroit-dearborn",
            extraction={"pets_allowed": True, "pet_fee": 2000,
                        "fee_basis": basis, "cleaning_fee": 10000,
                        "weight_limit": {"value": 35.0, "unit": "lb"},
                        "pet_count_limit": 2},
            withheld={}, block_text=_DEARBORN_BLOCK)
        assert comparison["fields"]["fee_basis"]["verdict"] == PILOT.MISMATCH
        assert not comparison["critical_field_exactness"]


# --------------------------------------------------------------------------- #
# Credential safety.
# --------------------------------------------------------------------------- #

def test_redaction_removes_every_fragment_of_the_endpoint(monkeypatch):
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-scraping_browser1:"
                       "s3cr3tpassword@brd.superproxy.io:9222")
    endpoint = client.browser_endpoint()
    leaky = ("connect ECONNREFUSED at %s while opening a session; user "
             "brd-customer-hl_test-zone-scraping_browser1 password "
             "s3cr3tpassword" % endpoint)
    assert client.contains_credential(leaky)
    cleaned = client.redact(leaky)
    assert not client.contains_credential(cleaned)
    assert "s3cr3tpassword" not in cleaned


def test_redaction_survives_the_url_escaping_playwright_applies(monkeypatch):
    """PTF-ST-LOUIS-PAID-ACQUISITION-002.

    The test above passes with an alphanumeric password, which is why the
    real leak went unseen for six work orders. Playwright re-serialises the
    endpoint as a URL before it echoes it in an error, so a password holding
    a URL-reserved character arrives percent-escaped, and the escaped
    spelling is a different string from the one the environment holds.

    A live ``407 Auth Failed`` printed the zone password this way.
    """
    password = "bLUE#JACK/ETS?123"
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-scraping_browser1:"
                       "%s@brd.superproxy.io:9222" % password)
    escaped = urllib.parse.quote(password, safe="")
    assert escaped != password

    leaky = ("BrowserType.connect_over_cdp: WebSocket error: "
             "wss://brd-customer-hl_test-zone-scraping_browser1-country-us:"
             "%s@brd.superproxy.io:9222/ 407 Auth Failed (wrong_password)"
             % escaped)
    assert client.contains_credential(leaky)
    cleaned = client.redact(leaky)
    assert not client.contains_credential(cleaned)
    assert password not in cleaned
    assert escaped not in cleaned
    # The diagnosis must survive the redaction, or the guard costs us the bug.
    assert "407 Auth Failed" in cleaned


def test_redaction_covers_the_country_pinned_username(monkeypatch):
    """Every capture path connects PINNED, so the raw username is never the
    string an error carries."""
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-scraping_browser1:"
                       "s3cr3tpassword@brd.superproxy.io:9222")
    pinned = client.browser_endpoint(country=client.DEFAULT_COUNTRY)
    assert "-country-us" in pinned
    assert client.contains_credential(pinned)
    assert not client.contains_credential(client.redact(pinned))


def test_redaction_is_indifferent_to_a_scheme_in_the_environment(monkeypatch):
    """``wss://`` may or may not be part of the variable; both spellings of
    the same secret must redact."""
    for raw in ("brd-customer-hl_test-zone-z1:s3cr3tpassword@brd.superproxy.io:9222",
                "wss://brd-customer-hl_test-zone-z1:s3cr3tpassword@brd.superproxy.io:9222"):
        monkeypatch.setenv(client.AUTH_ENV, raw)
        for spelling in (raw, raw.replace("wss://", ""), "wss://" + raw.replace("wss://", "")):
            assert client.contains_credential(spelling), spelling
            assert not client.contains_credential(client.redact(spelling)), spelling


def test_truncating_before_redacting_is_what_leaked_the_password(monkeypatch):
    """PTF-ST-LOUIS-PAID-ACQUISITION-002 -- the actual root cause.

    The redactor was never weak. The call site sliced the exception message to
    120 characters BEFORE handing it over, which cut the endpoint in half; the
    surviving prefix of the password was not a fragment the redactor knew, so
    there was nothing for it to remove and the report looked clean.

    This test states the property in both directions, because only the pair of
    them distinguishes a fixed ordering from a longer slice.
    """
    password = "bLUEJACKETS123"
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-scraping_browser1:"
                       "%s@brd.superproxy.io:9222" % password)
    endpoint = client.browser_endpoint()
    message = ("Error: BrowserType.connect_over_cdp: WebSocket error: %s/ "
               "407 Auth Failed (wrong_password)" % endpoint)

    # The old ordering: the slice lands inside the password.
    leaked = client.redact(message[:120])
    leaked_prefix = next((password[:n] for n in range(len(password), 3, -1)
                          if password[:n] in leaked), "")
    assert leaked_prefix, "fixture no longer reproduces the bug"
    assert not client.contains_credential(leaked), (
        "contains_credential cannot see a half password -- which is exactly "
        "why the guard reported clean")

    # The fixed ordering: nothing of the password survives, at any limit.
    for limit in (60, 120, 200, 400, 10_000):
        safe = client.redact_truncate(message, limit)
        assert password not in safe
        assert leaked_prefix not in safe, limit
        assert len(safe) <= limit


def test_redact_truncate_keeps_the_vendor_diagnosis(monkeypatch):
    """A guard that costs us the reason is not a good trade: the fix has to
    leave ``407 Auth Failed`` readable, or the next operator learns only that
    something went wrong."""
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-z1:s3cr3tpassword"
                       "@brd.superproxy.io:9222")
    message = ("Error: BrowserType.connect_over_cdp: WebSocket error: %s/ "
               "407 Auth Failed (wrong_password). Wrong customer password."
               % client.browser_endpoint())
    safe = client.redact_truncate(message, 400)
    assert "407 Auth Failed" in safe
    assert "wrong_password" in safe
    assert not client.contains_credential(safe)


def test_redaction_recurses_into_manifests(monkeypatch):
    monkeypatch.setenv(client.AUTH_ENV, "user123:pass456@brd.superproxy.io:9222")
    manifest = {"attempts": [{"detail": "wss://user123:pass456@brd.superproxy.io:9222"}]}
    assert client.contains_credential(manifest)
    assert not client.contains_credential(client.redact(manifest))


def test_the_cli_allowlist_refuses_the_command_that_leaks_the_zone_password():
    with pytest.raises(client.BrightDataUsageError):
        client._default_runner(["zones", "info", "scraping_browser1"])
    assert ("zones", "info") not in client.ALLOWED_CLI_ARGS


def test_usage_parsing():
    zone = ("Zone:            scraping_browser1\n"
            "Type:            browser_api / browser_api\n"
            "Plan bandwidth:  unknown\n\n"
            "Cost (this month):  $0.95\n"
            "Bandwidth used:     107.4 MB\n")
    parsed = client.parse_zone_budget(zone)
    assert parsed["cost_month_usd_minor"] == 95
    assert parsed["bandwidth_bytes"] == 107_400_000
    balance = client.parse_balance("Balance         $29.49\n"
                                   "Pending charge  $0.00\n")
    assert balance["balance_usd_minor"] == 2949
    assert balance["pending_charge_usd_minor"] == 0


def test_usage_never_raises_when_the_cli_is_missing():
    def broken(_args):
        raise client.BrightDataUsageError("no CLI")
    snapshot = client.read_usage("x", runner=broken)
    assert snapshot.available is False
    assert snapshot.notes


def test_unmoved_billing_is_pending_never_free():
    snapshot = client.UsageSnapshot(
        label="l", captured_at="t", zone="z", available=True,
        cost_month_usd_minor=95, bandwidth_bytes=107_400_000)
    delta = client.delta(snapshot, snapshot)
    assert delta["cost_status"] == "PENDING"
    assert "NOT evidence that the run was free" in delta["note"]


# --------------------------------------------------------------------------- #
# The evidence contract is used, not changed.
# --------------------------------------------------------------------------- #

def test_existing_contract_vocabularies_are_untouched():
    """Importing this package must not mutate a frozen vocabulary."""
    assert enums.ARTIFACT_KINDS == ("rendered_html", "operator_screenshot", "pdf")
    assert enums.FEE_BASES == ("per_night", "per_day", "per_stay")
    assert enums.BASIS_PER_DAY != enums.BASIS_PER_NIGHT
    assert PO.CAPTURE_METHODS == ("deterministic_fetch", "browser_assisted",
                                  "human_manual", "phone_contact")
    # The observation contract stands at 1.1.0 since PTF-ST-LOUIS-FOUNDER-
    # REMEDIATION-004 registered the two structured-pricing flag codes the
    # reader had been emitting unregistered. This assertion's purpose is that
    # IMPORTING a package must never mutate a vocabulary, and it still holds:
    # the change is a declared amendment, and 1.0.0 records -- which four
    # markets' committed stores carry -- still validate.
    # 1.2.0 since PTF-ST-LOUIS-FOUNDER-DECISIONS-006 admitted two OPTIONAL
    # fields carrying a human's ruling on a record. This assertion's purpose is
    # that IMPORTING a package must never mutate a vocabulary, and it still
    # holds: each step was a declared amendment, and every earlier version's
    # records still validate.
    # 1.3.0 since PTF-LOUISVILLE-FOUNDER-REMEDIATION-005 registered the seven
    # flag codes the readers emit that the closed vocabulary did not carry, so
    # the membrane was refusing whole observations over the NAME of a note.
    # Same purpose, same conclusion: a declared amendment, and every earlier
    # version's records still validate.
    assert PO.CONTRACT_VERSION == "1.3.0"
    assert PO.ACCEPTED_CONTRACT_VERSIONS == ("1.0.0", "1.1.0", "1.2.0", "1.3.0")
    assert EV.PUBLICATION_GRADE_REQUIRED == (
        "evidence_ref", "field", "quote", "source_url", "source_grade",
        "artifact_class", "artifact_sha256", "artifact_kind", "captured_at")


def test_the_pilot_declares_only_names_the_frozen_contract_knows():
    for slug in PILOT.BENCHMARK:
        assert slug in {s for s, _, _ in PILOT.TARGET_SPECS}
    result = MS.to_extraction(MS.parse_policy_block(_DEARBORN_BLOCK),
                              location="block")
    assert set(result.extraction) <= PO.EXTRACTION_FIELDS
    assert {f["code"] for f in result.flags} <= PO.FLAG_CODES
    assert set(result.withheld.values()) <= set(enums.WITHHOLDING_REASONS)


def test_gaps_are_reported_and_the_vocabulary_is_not_widened():
    codes = {gap.code for gap in PG.detect_gaps()}
    assert "GAP-01-NO-MACHINE-SCREENSHOT-KIND" in codes
    assert "GAP-02-NO-MANAGED-BROWSER-CAPTURE-METHOD" in codes
    # The gap is reported precisely because the member is still absent.
    assert not [k for k in enums.ARTIFACT_KINDS if "automat" in k]
    assert PG.CAPTURE_METHOD in PO.CAPTURE_METHODS


def test_a_missing_artifact_is_rejected_not_excused(tmp_path):
    verdict = PG.assess(
        evidence_items=[{"quote": "Pets Welcome", "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": True},
        source_url="https://www.marriott.com/x", captured_at="2026-08-18T00:00:00Z",
        ref_prefix="r", artifact_path=tmp_path / "absent.html",
        recorded_sha256="0" * 64, page_text_path=None, identity_confirmed=True)
    assert verdict.verdict == PG.REJECTED
    assert any("missing" in r for r in verdict.reasons)


def test_a_stitched_quote_is_rejected(tmp_path):
    html = tmp_path / "rendered.html"
    html.write_text("<html>Pets Welcome ... nine thousand characters ... "
                    "$150.00</html>", encoding="utf-8")
    text = tmp_path / "page-text.txt"
    text.write_text("Pets Welcome " + ("filler " * 2000) + "$150.00",
                    encoding="utf-8")
    verdict = PG.assess(
        evidence_items=[{"quote": "Pets Welcome $150.00",
                         "field_refs": ["pet_fee"]}],
        extraction={"pet_fee": 15000},
        source_url="https://www.marriott.com/x",
        captured_at="2026-08-18T00:00:00Z", ref_prefix="r",
        artifact_path=html, recorded_sha256=BC.sha256_file(html),
        page_text_path=text, identity_confirmed=True)
    assert verdict.verdict == PG.REJECTED
    assert not verdict.quotes_contiguous


def test_an_unconfirmed_identity_cannot_be_publication_grade(tmp_path):
    html = tmp_path / "rendered.html"
    html.write_text("Pets Welcome", encoding="utf-8")
    text = tmp_path / "page-text.txt"
    text.write_text("Pets Welcome", encoding="utf-8")
    verdict = PG.assess(
        evidence_items=[{"quote": "Pets Welcome", "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": True},
        source_url="https://www.marriott.com/x",
        captured_at="2026-08-18T00:00:00Z", ref_prefix="r",
        artifact_path=html, recorded_sha256=BC.sha256_file(html),
        page_text_path=text, identity_confirmed=False)
    assert verdict.verdict == PG.REJECTED


# --------------------------------------------------------------------------- #
# Authority is not touched.
# --------------------------------------------------------------------------- #

def test_the_pilot_writes_only_to_the_raw_tree_and_the_reports_directory():
    assert PILOT.RAW_ROOT.parts[-4:] == ("worker_runs", "pettripfinder",
                                         PILOT.PILOT_ID, "raw")
    for path in (PILOT.SUMMARY_REPORT, PILOT.PROPERTY_REPORT,
                 PILOT.COMPARISON_REPORT):
        assert path.parent == PILOT.REPORT_DIR
    source = inspect.getsource(PILOT)
    for authority in ("hotel_exclusions", "identity_routing",
                      "seed_businesses", "final_partition",
                      "hotel_policy_facts"):
        assert authority not in source, authority


def test_the_census_is_read_only():
    source = inspect.getsource(PILOT._census_rows)
    assert "write_text" not in source and "json.dump" not in source
    assert "READ ONLY" in source


def test_nothing_in_the_package_promotes_or_publishes():
    for module in (BC, MS, PG, PILOT, client, O):
        source = inspect.getsource(module)
        for forbidden in ("promote_", "publication_guard", "apply_decisions",
                          "PUBLISHED_PET_FRIENDLY"):
            assert forbidden not in source, (module.__name__, forbidden)


# --------------------------------------------------------------------------- #
# Committed reports, when a run has produced them.
# --------------------------------------------------------------------------- #

def _load(path: Path):
    if not path.exists():
        pytest.skip("%s has not been produced by a run yet" % path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_reports_carry_no_credential():
    for path in (PILOT.SUMMARY_REPORT, PILOT.PROPERTY_REPORT,
                 PILOT.COMPARISON_REPORT):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert not client.contains_credential(text), path.name
        for shape in _CREDENTIAL_SHAPES:
            assert shape not in text, (path.name, shape)


def test_committed_summary_declares_authority_unchanged():
    summary = _load(PILOT.SUMMARY_REPORT)
    for key in ("authority_changed", "policy_authority_changed",
                "exclusions_changed", "seed_authority_changed",
                "founder_approvals_changed", "partition_changed",
                "routing_authority_changed", "promotion_performed"):
        assert summary[key] is False, key
    assert summary["total"] == PILOT.PILOT_SIZE
    assert summary["false_verified_no_pets"] == 0


def test_committed_properties_are_the_five_and_carry_sane_artifacts():
    report = _load(PILOT.PROPERTY_REPORT)
    properties = report["properties"]
    assert len(properties) == PILOT.PILOT_SIZE
    assert {p["slug"] for p in properties} == {s for s, _, _ in PILOT.TARGET_SPECS}

    for prop in properties:
        assert len(prop["attempts"]) <= BC.MAX_ATTEMPTS
        for attempt in prop["attempts"]:
            assert attempt["outcome"] in O.OUTCOMES
            assert attempt["may_bear_evidence"] is (
                attempt["outcome"] == O.VALID)
        if not prop.get("successful_attempt"):
            assert prop["disposition"] == PILOT.CLAUDE_FALLBACK_REQUIRED
            assert "artifacts" not in prop
            continue
        files = prop["artifacts"]["files"]
        assert "rendered.html" in files and "page-text.txt" in files
        for name, entry in files.items():
            if not isinstance(entry, dict) or "sha256" not in entry:
                continue
            assert _SHA256_RE.match(entry["sha256"]), (prop["slug"], name)
            assert entry["bytes"] > 0


def test_committed_quotes_are_contiguous_in_the_committed_block():
    """Checkable in CI without the gitignored raw tree: every evidence quote
    must appear unbroken inside the policy block the report itself carries."""
    report = _load(PILOT.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        block = prop["policy_block_quote"]
        for item in prop["observation"]["evidence"]:
            assert EV.quote_is_contiguous(item["quote"], block), prop["slug"]


def test_committed_observations_still_validate_against_the_frozen_contract():
    report = _load(PILOT.PROPERTY_REPORT)
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        PO.validate_observation(prop["observation"])


def test_raw_artifact_hashes_rederive_when_the_raw_tree_is_present():
    report = _load(PILOT.PROPERTY_REPORT)
    checked = 0
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        for entry in prop["artifacts"]["files"].values():
            if not isinstance(entry, dict) or "path" not in entry:
                continue
            path = Path(entry["path"])
            if not path.exists():
                continue
            assert BC.sha256_file(path) == entry["sha256"], path
            checked += 1
    if checked == 0:
        pytest.skip("the gitignored raw artifact tree is not present here")


# --------------------------------------------------------------------------- #
# A blank crop is not a screenshot.
# --------------------------------------------------------------------------- #

def _png(tmp_path, name, pixels):
    Image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    path = tmp_path / name
    image = Image.new("RGB", (4, 4), (255, 255, 255))
    for xy, colour in pixels.items():
        image.putpixel(xy, colour)
    image.save(path)
    return path


def test_a_uniform_crop_is_detected_as_blank(tmp_path):
    assert BC.image_is_blank(_png(tmp_path, "flat.png", {})) is True


def test_a_crop_with_content_is_not_blank(tmp_path):
    assert BC.image_is_blank(
        _png(tmp_path, "ink.png", {(1, 1): (0, 0, 0)})) is False


def test_a_non_image_is_undecidable_rather_than_blank(tmp_path):
    path = tmp_path / "not-an-image.png"
    path.write_bytes(b"not a png")
    assert BC.image_is_blank(path) is None


def test_the_screenshot_budget_exceeds_playwrights_default():
    """Run 1 lost a session to the 30 s default on a full-page capture."""
    assert BC.SCREENSHOT_TIMEOUT_MS > 30_000


def test_the_harness_notes_record_both_run_one_defects():
    joined = " ".join(PILOT.HARNESS_NOTES).lower()
    assert "timeout 30000ms" in joined
    assert "white rectangle" in joined
    assert "neither was a refusal" in joined


def test_a_blank_policy_crop_is_never_recorded_as_an_artifact():
    """Committed reports must not name a policy-section.png that is blank.

    Checkable only where the gitignored raw tree exists; the point of the
    check is that the file-existence count and the image-content count agree.
    """
    report = _load(PILOT.PROPERTY_REPORT)
    checked = 0
    for prop in report["properties"]:
        if not prop.get("successful_attempt"):
            continue
        entry = (prop["artifacts"]["files"] or {}).get("policy-section.png")
        if not entry:
            # Correctly refused. The manifest must say why.
            assert (prop["artifacts"].get("policy_section") or {}).get(
                "captured") is False
            continue
        path = Path(entry["path"])
        if not path.exists():
            continue
        assert BC.image_is_blank(path) is not True, prop["slug"]
        checked += 1
    if checked == 0:
        pytest.skip("the gitignored raw artifact tree is not present here")
