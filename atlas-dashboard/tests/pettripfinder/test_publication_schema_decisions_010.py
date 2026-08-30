"""PTF-ST-LOUIS-PUBLICATION-SCHEMA-DECISIONS-010 -- four founder rulings, applied.

Each ruling widens what may be PUBLISHED. None widens what may be INFERRED, and
that distinction is what these tests pin: every decision is off by default, gated
on conditions read from the evidence, and paired with the case it must still
refuse.

Schema 1.2 -> 1.3 is additive. The tests that matter most are the compatibility
ones: a 1.2 record must still validate, or five live markets would need
migrating to stay legal.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

PREPARED_CONTRACT = ("launch_packages/pettripfinder/st_louis_publication_010/"
                     "release_contract.st-louis-mo.prepared.json")

import pytest

from pettripfinder.indianapolis_promoted_state import PROMOTED_PET_FRIENDLY

from scripts.pettripfinder import market_policy_package_cli as PP
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as PS

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- #
# The amendment itself
# --------------------------------------------------------------------------- #

class TestSchema13IsAdditive:
    def test_the_version_moved_and_1_2_stays_canonical(self):
        """1.2 did not become "legacy" -- it became "not the newest".

        The first draft of this test asserted ``"1.2" in
        LEGACY_POLICY_SCHEMA_VERSIONS`` and that set really was widened to say
        so, which was a genuine defect: that set is the list of PRE-CANONICAL
        schemas the compatibility reader parses as display strings. A canonical
        record holds an object where that reader expects ``"$50.00"``, so the
        widening silently emptied every fee on all five live markets. What the
        amendment actually did is add a version to the CANONICAL family.
        """
        assert enums.POLICY_SCHEMA_VERSION == "1.3"
        assert "1.2" not in enums.LEGACY_POLICY_SCHEMA_VERSIONS
        assert enums.is_canonical_policy_schema("1.2")
        assert enums.is_canonical_policy_schema("1.3")
        assert not enums.is_canonical_policy_schema("1.1")

    def test_an_additive_amendment_does_not_unpublish_a_live_market(self):
        """The regression this pair exists to stop.

        ``publication_042`` gated publishability on ``schema_version ==
        POLICY_SCHEMA_VERSION``, so bumping the constant made all 73 Milwaukee
        records non-publishable without one fact changing. The founder's
        Decision 2 required the opposite: existing 1.2 records stay valid and no
        live market needs migrating merely to remain valid.
        """
        import json as _json
        from scripts.pettripfinder import canonical_view as _CV
        # The cohort is DERIVED, not listed. What this proves is that a package
        # left at 1.2 still publishes -- so it must follow the markets that are
        # actually still at 1.2, not a list that has to be edited every time one
        # of them legitimately migrates (PTF-PITTSBURGH-HARDENED-SYNC-004 moved
        # pittsburgh-pa to 1.3 to reach other_charges[].refundable_stated).
        # Editing the list would have been the one change that silently drops
        # the market this guard was still covering.
        candidates = ("milwaukee-wi", "pittsburgh-pa", "dayton-oh",
                      "cleveland-akron-canton-oh")
        packages = {}
        for market in candidates:
            with open(PKG + "hotel_policy_facts_%s.json" % market,
                      encoding="utf-8") as handle:
                packages[market] = _json.load(handle)
        still_1_2 = [m for m, p in packages.items()
                     if p["schema_version"] == "1.2"]
        assert still_1_2, ("no market is on 1.2 any more, so this guard is no "
                           "longer proving that a 1.2 package stays publishable")
        for market in still_1_2:
            package = packages[market]
            assert package["schema_version"] == "1.2"
            assert enums.is_canonical_policy_schema(package["schema_version"])
            priced = [h for h in package["hotels"] if "pet_fee" in h["facts"]]
            assert priced, market
            for hotel in priced:
                entry = dict(hotel)
                entry.setdefault("schema_version", package["schema_version"])
                # The canonical branch, not the display-string reader.
                assert _CV.display_facts(entry).get("pet_fee"), (
                    market, hotel.get("key"))

    def test_a_1_2_record_still_validates_untouched(self):
        # If this fails, five live markets need migrating to stay legal.
        legacy = {"pets_allowed": True,
                  "weight_limit": {"value": 50, "unit": "lb",
                                   "operator": "lte", "scope": "per_pet"},
                  "pet_fee": {"amount_cents": 2500, "currency": "USD"},
                  "other_charges": [{"amount_cents": 5000, "currency": "USD",
                                     "kind": "refundable_deposit",
                                     "refundable": True}]}
        assert PS.validate_facts(legacy) == ()

    def test_every_LIVE_market_package_still_validates(self):
        # The four markets actually serving production. 245 records.
        for market in ("pittsburgh-pa", "milwaukee-wi", "dayton-oh",
                       "cleveland-akron-canton-oh"):
            package = _load("hotel_policy_facts_%s.json" % market)
            for record in package["hotels"]:
                assert PS.validate_facts(record["facts"]) == (), \
                    "%s / %s" % (market, record["key"])

    def test_indianapolis_has_five_PRE_EXISTING_failures_not_caused_here(self):
        # Indianapolis is SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED and serves no
        # production traffic. Five of its eight records lack weight_limit.scope
        # -- the SAME latent gap 010 surfaced in St. Louis, and it would bite
        # the moment anyone tried to publish that market. Recorded here so the
        # next reader does not mistake it for fallout from the 1.3 amendment:
        # every failure names weight_limit, and 1.3 changed nothing about
        # weight.
        # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 re-projected the package through market_policy_package_cli
        # with founder decision 1 applied, so the five weight_limit.scope gaps
        # are gone: every record validates. Kept as the record that they were
        # pre-existing and never fallout from the 1.3 amendment.
        package = _load("hotel_policy_facts_indianapolis-in.json")
        failures = [(h["key"], PS.validate_facts(h["facts"]))
                    for h in package["hotels"] if PS.validate_facts(h["facts"])]
        assert failures == []
        assert len(package["hotels"]) == PROMOTED_PET_FRIENDLY

    def test_absence_of_both_additions_remains_valid(self):
        assert PS.validate_facts({"pets_allowed": True}) == ()

    def test_the_vocabulary_is_still_closed(self):
        issues = PS.validate_facts({"pets_allowed": True, "invented": 1})
        assert any(i.code == "UNKNOWN_FIELD" for i in issues)


# --------------------------------------------------------------------------- #
# Decision 1 -- weight normalisation
# --------------------------------------------------------------------------- #

class TestWeightNormalisation:
    def test_it_is_off_by_default(self):
        facts, _ = PP.project_facts(
            {"pets_allowed": True, "weight_limit": {"value": 50, "unit": "lb"}},
            [{"quote": "maximum 50 pounds", "field_refs": ["weight_limit"]}])
        assert "operator" not in facts["weight_limit"]

    @pytest.mark.parametrize("quote", [
        "maximum 50 pounds", "pet weight limit 50 lb", "pets up to 50 pounds",
        "Max weight 60 lbs", "20 pounds max", "35lbs or less", "max. 30lbs",
        "Weight limit of 50lbs", "under 40 pounds"])
    def test_a_blanket_maximum_is_eligible(self, quote):
        ok, why = PP.weight_normalisation_eligible({}, [quote])
        assert ok, why

    @pytest.mark.parametrize("quote", [
        "combined weight limit of 80 lbs",
        "80 lbs total for both pets",
        "pets together may not exceed 80 pounds"])
    def test_combined_weight_language_is_refused(self, quote):
        # Founder conditions 3 and 4. A shared ceiling is a different fact.
        ok, why = PP.weight_normalisation_eligible({}, [quote])
        assert not ok and "combined or shared" in why

    def test_a_separate_combined_weight_limit_field_refuses(self):
        ok, why = PP.weight_normalisation_eligible(
            {"combined_weight_limit": {"value": 80, "unit": "lb"}},
            ["maximum 50 pounds"])
        assert not ok and "combined_weight_limit" in why

    def test_a_stated_scope_is_never_overridden(self):
        # Founder condition 5.
        ok, why = PP.weight_normalisation_eligible(
            {"weight_limit": {"value": 50, "unit": "lb", "scope": "per_species"}},
            ["maximum 50 pounds"])
        assert not ok and "already stated" in why

    def test_no_quote_means_no_normalisation(self):
        ok, why = PP.weight_normalisation_eligible({}, [])
        assert not ok and "no quote" in why

    def test_vague_wording_is_refused(self):
        ok, why = PP.weight_normalisation_eligible({}, ["pets 50 lbs"])
        assert not ok and "does not clearly state a maximum" in why

    def test_normalisation_records_that_it_happened_and_keeps_the_source(self):
        facts, notes = PP.project_facts(
            {"pets_allowed": True, "weight_limit": {"value": 50, "unit": "lb"}},
            [{"quote": "maximum 50 pounds", "field_refs": ["weight_limit"]}],
            normalize_weight=True)
        assert facts["weight_limit"]["operator"] == "lte"
        assert facts["weight_limit"]["scope"] == enums.WEIGHT_SCOPE_PER_PET
        note = " ".join(notes)
        assert "FOUNDER-NORMALISED" in note
        assert "maximum 50 pounds" in note

    def test_a_stated_operator_is_not_overwritten(self):
        facts, _ = PP.project_facts(
            {"pets_allowed": True,
             "weight_limit": {"value": 50, "unit": "lb", "operator": "lt",
                              "scope": "per_pet"}},
            [{"quote": "under 50 pounds", "field_refs": ["weight_limit"]}],
            normalize_weight=True)
        assert facts["weight_limit"]["operator"] == "lt"


# --------------------------------------------------------------------------- #
# Decision 2 -- service-animal statements
# --------------------------------------------------------------------------- #

class TestServiceAnimalStatements:
    """Decision 2, in the namespace the contract reserves for it.

    010's first draft added ``service_animal_exception`` to the FACTS block.
    ``policy_schema.validate_record`` has rejected exactly that since long
    before this work order -- MISPLACED_FIELD, "a legal access category must
    not sit in the commercial-terms namespace: a weight limit beside it invites
    something to apply one to the other" -- which is the founder's own Decision
    2 constraint, already enforced. The draft passed only because it validated
    ``facts`` and never the record. The statement lives on the record envelope.
    """

    def test_a_statement_inside_facts_is_still_rejected(self):
        issues = PS.validate_record({
            "identity_key": "comfort inn alton near i 255", "name": "X",
            "facts": {"pets_allowed": True,
                      "service_animal_exception": "Service animals welcome."}})
        assert any(i.code == "MISPLACED_FIELD" for i in issues)
        assert "service_animal_exception" not in PS.KNOWN_FACT_FIELDS

    def test_the_envelope_carries_the_property_s_exact_words(self):
        quote = "Service animals are permitted, without charge."
        record = {"identity_key": "comfort inn alton near i 255", "name": "X",
                  "facts": {"pets_allowed": True},
                  "service_animal_statement": {
                      "stated": True, "charges_stated": enums.SERVICE_ANIMAL_NO_CHARGE,
                      "quote": quote}}
        assert PS.validate_record(record) == ()

    def test_the_quote_must_be_prose_and_never_empty(self):
        def check(value):
            return PS.validate_record({
                "identity_key": "comfort inn alton near i 255", "name": "X",
                "facts": {"pets_allowed": True},
                "service_animal_statement": {
                    "stated": True,
                    "charges_stated": enums.SERVICE_ANIMAL_NOT_ADDRESSED,
                    "quote": value}})
        assert any(i.code == "NOT_STRING" for i in check(42))
        assert any(i.code == "NULL_FOR_SILENCE" for i in check("   "))

    def test_the_amendment_is_additive_a_statement_may_omit_the_quote(self):
        # Every live market's statements predate the quote field.
        assert PS.validate_record({
            "identity_key": "comfort inn alton near i 255", "name": "X",
            "facts": {"pets_allowed": True},
            "service_animal_statement": {
                "stated": True,
                "charges_stated": enums.SERVICE_ANIMAL_NOT_ADDRESSED}}) == ()

    def test_it_is_never_derived_from_pet_terms(self):
        # A row with pet terms and no service-animal sentence gets no statement.
        assert PP.project_service_animal_statement(
            {"pets_allowed": True, "pet_fee": 2500}) is None

    def test_a_charge_is_never_asserted_by_projection(self):
        """``charge_stated`` is unreachable.

        Claiming a property charges for a service animal is a claim no
        projection should make from prose, so the reader produces only a stated
        absence of charge or "the statement does not address charges".
        """
        produced = set()
        for text in ("Service animals are permitted, without charge.",
                     "ADA defined service animals are welcome at this hotel.",
                     "Service animals will be exempt from this charge.",
                     "Service Animals - ADA-defined service animals welcome."):
            produced.add(PP.project_service_animal_statement(
                {"service_animal_exception": text})["charges_stated"])
        assert produced == {enums.SERVICE_ANIMAL_NO_CHARGE,
                            enums.SERVICE_ANIMAL_NOT_ADDRESSED}
        assert enums.SERVICE_ANIMAL_CHARGE_STATED not in produced

    def test_the_corrected_st_louis_statements_survive_exactly(self):
        # PTF-ST-LOUIS-FOUNDER-REMEDIATION-004 trimmed pet terms that had been
        # glued onto the front of these sentences. Publishing the untrimmed form
        # would state that service animals carry a fee and a weight cap.
        package = {h["key"]: h for h in
                   _load("hotel_policy_facts_st-louis-mo.json")["hotels"]}
        for key in ("comfort inn and suites saint louis lafayette square",
                    "radisson hotel fairview heights st louis"):
            statement = package[key]["service_animal_statement"]
            assert statement["quote"] == ("Service animals are permitted, "
                                          "without charge.")
            assert statement["charges_stated"] == enums.SERVICE_ANIMAL_NO_CHARGE
            assert "pound" not in statement["quote"].lower()
            assert "per night" not in statement["quote"].lower()

    def test_no_published_statement_carries_a_pet_fee_or_weight(self):
        seen = 0
        for record in _load("hotel_policy_facts_st-louis-mo.json")["hotels"]:
            assert "service_animal_exception" not in record["facts"], record["key"]
            statement = record.get("service_animal_statement")
            if not statement:
                continue
            seen += 1
            lowered = statement["quote"].lower()
            assert "per night" not in lowered, record["key"]
            assert not any(w in lowered for w in ("lbs max", "pounds max")),                 record["key"]
        assert seen == 41


# --------------------------------------------------------------------------- #
# Decision 3 -- fee cap qualifier
# --------------------------------------------------------------------------- #

class TestFeeCapQualifier:
    def test_it_is_off_by_default(self):
        facts, _ = PP.project_facts({
            "pets_allowed": True,
            "fee_cap": {"amount_minor": 7500, "currency": "USD"}})
        assert "qualifier_stated" not in facts["fee_cap"]

    def test_false_means_the_source_stated_no_qualifier(self):
        facts, notes = PP.project_facts(
            {"pets_allowed": True,
             "fee_cap": {"amount_minor": 7500, "currency": "USD",
                         "basis": "per_stay"}},
            cap_qualifier_stated=False)
        assert facts["fee_cap"]["qualifier_stated"] is False
        note = " ".join(notes)
        assert "never that no qualifier exists" in note

    def test_the_distinction_is_carried_in_the_contract_semantics(self):
        contract = json.loads(pathlib.Path(
            PREPARED_CONTRACT
        ).read_text(encoding="utf-8"))
        note = contract["policy_package"]["structured_pricing_note"]
        assert "NOT that no qualifier exists" in note

    def test_a_source_stated_qualifier_is_not_overwritten(self):
        facts, _ = PP.project_facts(
            {"pets_allowed": True,
             "fee_cap": {"amount_minor": 7500, "currency": "USD",
                         "qualifier_stated": True}},
            cap_qualifier_stated=False)
        assert facts["fee_cap"]["qualifier_stated"] is True


# --------------------------------------------------------------------------- #
# Decision 4 -- pet deposit
# --------------------------------------------------------------------------- #

class TestPetDeposit:
    def test_a_deposit_never_merges_into_the_pet_fee(self):
        facts, _ = PP.project_facts(
            {"pets_allowed": True, "pet_fee": 1500, "fee_currency": "USD",
             "fee_basis": "per_night", "pet_deposit": 5000},
            [{"quote": "$50 refundable deposit", "field_refs": ["pet_deposit"]}])
        assert facts["pet_fee"]["amount_cents"] == 1500
        assert facts["other_charges"][0]["amount_cents"] == 5000
        assert facts["other_charges"][0]["description"] == "pet deposit"

    def test_a_stated_refundable_deposit_is_carried(self):
        facts, _ = PP.project_facts(
            {"pets_allowed": True, "pet_deposit": 5000, "fee_currency": "USD"},
            [{"quote": "$50 refundable deposit", "field_refs": ["pet_deposit"]}])
        charge = facts["other_charges"][0]
        assert charge["refundable"] is True
        assert charge["kind"] == "refundable_deposit"
        assert charge["refundable_stated"] is True

    def test_an_unstated_refundability_is_declared_not_invented(self):
        # The STOP subcase. other_charges.refundable is required and is never
        # inferred from the word "deposit", so 1.3 lets the record say the
        # source was silent.
        facts, _ = PP.project_facts(
            {"pets_allowed": True, "pet_deposit": 7500, "fee_currency": "USD"},
            [{"quote": "deposit: 75 USD", "field_refs": ["pet_deposit"]}])
        charge = facts["other_charges"][0]
        assert charge["refundable_stated"] is False
        assert "refundable" not in charge
        assert PS.validate_facts(facts) == ()

    def test_refundability_is_never_read_off_the_word_deposit(self):
        assert PP.deposit_refundability(["deposit of 50.00 USD"]) is None
        assert PP.deposit_refundability(["non-refundable fee"]) is False
        assert PP.deposit_refundability(["$50 refundable deposit"]) is True

    def test_a_charge_omitting_both_fields_is_still_refused(self):
        issues = PS.validate_facts({"pets_allowed": True, "other_charges": [
            {"amount_cents": 5000, "currency": "USD",
             "kind": "incidental_deposit"}]})
        assert any(i.code == "MISSING_REQUIRED" for i in issues)


# --------------------------------------------------------------------------- #
# The committed package and contract
# --------------------------------------------------------------------------- #

class TestTheCommittedPackage:
    def test_all_82_records_validate(self):
        package = _load("hotel_policy_facts_st-louis-mo.json")
        assert package["count"] == len(package["hotels"]) == 82
        assert package["refusals"] == []
        for record in package["hotels"]:
            assert PS.validate_facts(record["facts"]) == (), record["key"]

    def test_it_is_at_1_3_and_now_published(self):
        # 010 wrote this package with published:false and stopped there.
        # PTF-ST-LOUIS-REGISTER-PUBLISH-011 registered the market and flipped
        # the flag; the schema decision 010 made is unchanged and is what the
        # published records still satisfy.
        package = _load("hotel_policy_facts_st-louis-mo.json")
        assert package["schema_version"] == "1.3"
        assert package["published"] is True
        assert package["publication"]["work_order"] == (
            "PTF-ST-LOUIS-REGISTER-PUBLISH-011")
        # Dated from the founder's decision, never from the clock: a timestamp
        # would make every rebuild a different file and break the sha256 the
        # release contract pins.
        assert package["publication"]["published_for_decision_dated"] == "2026-08-23"
        assert package["publication"]["deployed"] is False

    def test_48_records_record_their_founder_normalisation(self):
        package = _load("hotel_policy_facts_st-louis-mo.json")
        normalised = [h for h in package["hotels"]
                      if any("FOUNDER-NORMALISED" in n
                             for n in h.get("projection_notes") or ())]
        assert len(normalised) == 48
        for record in normalised:
            assert record["facts"]["weight_limit"]["operator"] == "lte"
            assert record["facts"]["weight_limit"]["scope"] == "per_pet"

    def test_five_deposits_are_distinct_charges(self):
        package = _load("hotel_policy_facts_st-louis-mo.json")
        deposits = [h for h in package["hotels"]
                    if any(c.get("description") == "pet deposit"
                           for c in h["facts"].get("other_charges") or ())]
        assert len(deposits) == 5
        both = [h for h in deposits if "pet_fee" in h["facts"]]
        assert both, "a hotel may carry both a fee and a deposit"

    def test_no_forbidden_token_ships_in_the_package(self):
        contract = json.loads(pathlib.Path(
            PREPARED_CONTRACT
        ).read_text(encoding="utf-8"))
        raw = pathlib.Path(
            PKG + "hotel_policy_facts_st-louis-mo.json").read_text(
                encoding="utf-8")
        for token in contract["forbidden_output_tokens"]:
            assert token not in raw, token


class TestTheCommittedContract:
    @staticmethod
    def _contract():
        return json.loads(pathlib.Path(
            PREPARED_CONTRACT
        ).read_text(encoding="utf-8"))

    def test_the_prepared_contract_records_why_it_waited(self):
        """The live directory IS the verified set.

        ``release_contracts.verify_all()`` verifies every contract it finds in
        ``deploy/netlify/release_contracts/`` and ``verify_contract`` raises on a
        market with no registered contract, so a prepared contract placed there
        would have broken verification for EVERY market. Milwaukee hit this exact
        wall (``publication_037.PREPARED_CONTRACT``); 010 followed the precedent
        and stopped. This file is that decision, kept as written.
        """
        assert self._contract()["market_id"] == "st-louis-mo"
        assert self._contract()["status"] == "PREPARED_NOT_REGISTERED"

    def test_the_live_contract_is_now_installed_and_verifies(self):
        from scripts.pettripfinder import release_contracts as RC
        assert "st-louis-mo" in RC.available_market_ids()
        live = RC.load_contract("st-louis-mo")
        assert live["status"] == "LIVE"
        assert RC.verify_contract("st-louis-mo") == []

    def test_it_pins_the_package_by_hash_count_and_version(self):
        from scripts.pettripfinder import release_contracts as RC
        block = RC.load_contract("st-louis-mo")["policy_package"]
        raw = pathlib.Path(block["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == block["expected_sha256"]
        assert block["expected_record_count"] == 82
        assert block["expected_schema_version"] == "1.3"

    def test_it_carries_all_27_minimum_gates(self):
        assert len(self._contract()["minimum_release_gates"]) == 27

    def test_unevaluable_gates_are_listed_not_skipped(self):
        blocked = self._contract()["gates_not_evaluable_offline"]
        gates = set(self._contract()["minimum_release_gates"])
        assert set(blocked["blocked_by_registration"]) <= gates
        assert set(blocked["requires_a_build"]) <= gates
        assert len(blocked["blocked_by_registration"]) == 4
        assert len(blocked["requires_a_build"]) == 12

    def test_it_grants_no_deployment(self):
        auth = self._contract()["deployment_authorization"]
        assert auth["grants_deployment"] is False
        assert auth["asserts_market_complete"] is False

    def test_routing_is_market_prefixed_and_not_reinvented(self):
        routes = self._contract()["routes"]
        assert routes["route_mode"] == "market_prefixed"
        assert routes["market_slug"] == "st-louis-mo"
        assert routes["hotel_route_count"] == 82

    def test_it_records_the_superseded_and_held_identities(self):
        prov = self._contract()["provenance"]
        assert set(prov["superseded_identities"]) == {"wingate at wyndham",
                                                      "doubletree"}
        assert prov["held_identities"] == ["days inn and suites pontoon beach"]
        assert prov["signed_authority_total"] == 119

    def test_reconciliation_sums_to_the_census(self):
        rec = self._contract()["reconciliation"]
        assert rec["published_pet_friendly"] == 82
        assert rec["verified_no_pets"] == 37
        assert rec["resolved"] == 119
        assert rec["resolved"] + rec["unresolved"] == rec["confirmed_identities"] == 357

    def test_the_market_is_now_registered_with_an_authority_shard(self):
        # 010 asserted the opposite, deliberately: registering a market
        # invalidates the signed deployment authorization, so it was a founder
        # step and not a side effect of a schema decision.
        # PTF-ST-LOUIS-REGISTER-PUBLISH-011 took that step.
        assert pathlib.Path(PKG + "markets/st-louis-mo.json").exists()
        assert not pathlib.Path(PKG + "markets/pending/st-louis-mo.json").exists()
        shard = pathlib.Path(PKG + "markets/authority/st-louis-mo")
        assert shard.is_dir()
        assert (shard / "seed_businesses.csv").is_file()
        assert (shard / "hotel_exclusions.json").is_file()
