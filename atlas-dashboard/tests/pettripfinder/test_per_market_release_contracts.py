"""PTF-PER-MARKET-RELEASE-CONTRACTS-001 -- per-market release contracts.

The defect these tests exist to prevent: ONE committed release contract,
calibrated to Columbus, gating every market's build. Cleveland's nineteen
verified hotels were compared against Columbus's eighty-eight, and the assembler
fail-closed on a number that was never about Cleveland.

The tests are therefore organised around REUSE, not around parsing:

  * every configured market has its own contract, and no contract can stand in
    for another market's -- checked both at the loader and at the assembler;
  * each contract agrees with its OWN market's committed authority, and
    disagrees with every other market's;
  * the numbers that are market-calibrated are pairwise distinct, while the
    blocks that describe the shared deployment TARGET stay identical (drift
    between three copies of the publish rules is the other failure mode a
    per-market split introduces);
  * a passing contract is stated, in the document and in the manifest, to be a
    structural statement rather than a deployment authorization.

The expected reconciliation figures below are explicit constants, deliberately
not read back from the files they check. A test that recomputes its own
expectation from the artifact under test proves only that arithmetic is
deterministic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder.assemble_netlify_bundle import (
    AssembleError,
    assemble,
    load_release_contract,
)
from scripts.pettripfinder.market_context import resolve_market
from scripts.pettripfinder.markets import load_markets
from scripts.pettripfinder.release_contracts import (
    CONTRACT_SCHEMA,
    RECONCILIATION_FIELDS,
    RELEASE_CONTRACTS_DIR,
    REPO_ROOT,
    ReleaseContractError,
    available_market_ids,
    contract_disagreements,
    contract_path,
    derive_authority,
    load_contract,
    verify_contract,
)

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
INDIANAPOLIS = "indianapolis-in"
PITTSBURGH = "pittsburgh-pa"
#: PTF-MILWAUKEE-PUBLICATION-042 published Milwaukee, so it now has verified
#: inventory and therefore must have a contract. The invariant below is
#: unchanged -- every market that CAN release has one -- and this is the list
#: of markets that can.
MILWAUKEE = "milwaukee-wi"
#: PTF-ST-LOUIS-REGISTER-PUBLISH-011 registered and published St. Louis, so it
#: has verified inventory and must have a contract on the same rule.
ST_LOUIS = "st-louis-mo"
#: PTF-LOUISVILLE-PUBLICATION-008 added the eighth contract.
LOUISVILLE = "louisville-ky"

GRAND_RAPIDS = "grand-rapids-holland-mi"

MARKETS = (COLUMBUS, CLEVELAND, DAYTON, PITTSBURGH, INDIANAPOLIS, MILWAUKEE,
           ST_LOUIS, LOUISVILLE, GRAND_RAPIDS)

#: The reconciliation each market's committed authority is expected to state, as
#: (confirmed, published, verified_no_pets, resolved, unresolved). ``None`` means
#: the market commits no identity census, so its confirmed universe is not a
#: derivable fact -- absent is a fact, zero would be a claim.
EXPECTED_RECONCILIATION = {
    # 163 identities, 35 published, 14 verified-no-pets, 49 resolved and 114
    # unresolved. The census is the 163-row recensus, promoted into the pinned
    # path by PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024; the
    # 120-identity document the 2025 build pinned is kept beside it, and the
    # ten prior identities it no longer names were each absorbed into a fresh
    # sighting of the same building. Like Louisville, this market records no
    # OUT_OF_CURRENT_CATEGORY identity, so unresolved is the remainder.
    "grand-rapids-holland-mi": (163, 35, 14, 49, 114),
    # 166 identities, 46 published, 17 verified-no-pets, 63 resolved and 103
    # unresolved -- and unresolved is COUNTED as the remainder because this
    # market records no OUT_OF_CURRENT_CATEGORY identity, exactly as Milwaukee
    # and St. Louis do (PTF-LOUISVILLE-PUBLICATION-008).
    "louisville-ky": (166, 46, 17, 63, 103),
    # PTF-CENSUS-PARTITION-NORMALIZATION-001 gave Columbus the census it never
    # had: 112 identities reconstructed from committed authority alone. Its
    # confirmed and unresolved figures were `None` because nothing could
    # state them; now the partition counts 8 unresolved, and `resolved` is
    # 104 rather than 102 because it includes the two OUT_OF_CURRENT_CATEGORY
    # rulings -- a category exit settles an identity as finally as a refusal.
    COLUMBUS: (112, 88, 14, 104, 8),
    # PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 published the two Drury
    # properties worker 003 established on their own domain: 19 -> 21, and
    # unresolved 161 -> 159. The other four candidates it reviewed did NOT
    # publish -- three are readiness POLICY_PARTIAL (marketing-only Wyndham
    # copy) and one is a membrane M10 identity rejection -- so they stay in
    # the unresolved 159 rather than moving the resolved figure.
    # PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001 applied the founder's 45
    # rulings on the 49-row attended-capture packet: twenty artifact-backed
    # publications (21 -> 41) and twenty-three first-party refusals
    # (8 -> 31 verified-no-pets), so resolved was 72 and unresolved 116.
    # PTF-CLEVELAND-PASS3-FOUNDER-DECISIONS-001 then applied the founder's
    # 44 rulings on the 68-row driveable-queue packet: forty artifact-backed
    # publications (41 -> 81) and four first-party refusals (31 -> 35), so
    # resolved is 116 and unresolved 72.
    # PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 then applied 23 rulings:
    # 18 publications (81 -> 99, incl. two authorized renames) and 5
    # refusals (35 -> 40), so resolved is 139 and unresolved 49.
    CLEVELAND: (188, 99, 40, 139, 49),
    # PTF-DAYTON-CANDIDATE-PROMOTION-001 promoted the reviewed
    # dayton-recovery-002 candidates: 33 -> 44 published (eleven new) and
    # 6 -> 7 verified-no-pets (Hotel Versailles). Two of the fourteen proposals
    # were not promoted -- readiness POLICY_PARTIAL -- so they stayed unresolved,
    # which is why unresolved fell to 78 and not to 76.
    #
    # PTF-DAYTON-WORK-BROWSER-INTEGRATION-001: 44 -> 47 and 7 -> 8. The ChatGPT
    # Work browser pass published nothing itself -- it carries no artifact of
    # any page -- but it pointed at four hash-verified captures: two Best
    # Westerns and one Extended Stay America whose visible pet policy publishes,
    # and Best Western Celina's "Pets are not accepted." All four had been
    # written off as brand-platform ACCESS_BLOCKED by a static fetch.
    DAYTON: (129, 47, 8, 55, 74),
    # PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001 applied the twenty founder
    # decisions from the Pass 1 packet: 17 artifact-backed publications, 2
    # first-party refusals, and the Distrikt -> Joinery identity rename
    # (Joinery stays unresolved pending a clean recapture under the new
    # identity). resolved is 22 rather than 19 because the three census
    # NOT_LODGING rulings are projected into the registry as
    # OUT_OF_CURRENT_CATEGORY -- the Columbus mechanic -- and unresolved is
    # COUNTED from the committed final partition.
    # PTF-PITTSBURGH-PASS2-DECISION-APPLICATION-001 added 9 more publications
    # (17 -> 26) and 2 more verified-no-pets (2 -> 4) on top of the Pass 1
    # figures; resolved = 26 + 4 + 3 out_of_current_category = 33, unresolved
    # is COUNTED from the committed final partition (63).
    PITTSBURGH: (96, 26, 4, 33, 63),
    INDIANAPOLIS: (153, 8, 4, 12, 141),
    # PTF-MILWAUKEE-PUBLICATION-042. 147 confirmed identities; 73 published
    # pet-friendly and 27 verified-no-pets, both founder-approved across two
    # sittings (036 and 040); resolved = 73 + 27 = 100; unresolved is COUNTED
    # from the committed final partition (47), and is UNKNOWN rather than
    # negative evidence.
    MILWAUKEE: (147, 73, 27, 100, 47),
    # PTF-ST-LOUIS-REGISTER-PUBLISH-011. 357 confirmed identities from the
    # generic discovery census; 82 published pet-friendly and 37
    # verified-no-pets, founder-signed across two sittings (005 and 007) and
    # cleaned of two duplicate signatures by 008B; resolved = 82 + 37 = 119,
    # with no OUT_OF_CURRENT_CATEGORY ruling in this market. unresolved is 238
    # and is UNKNOWN, never negative evidence: 153 identities were never
    # reached by a lane that could answer, 66 hold insufficient evidence, 16
    # served a page that stated nothing, and 1 is held on an unsettled identity.
    ST_LOUIS: (357, 82, 37, 119, 238),
}

#: Columbus's published-profile count. The single number this whole sprint
#: exists to stop leaking into another market's release gates.
COLUMBUS_PROFILE_COUNT = 88

#: Contract sections that describe the shared deployment TARGET (one Netlify
#: site, one apex domain, one publish root) rather than any market.
TARGET_SECTIONS = ("canonical", "publish", "forbidden_output_tokens",
                   "minimum_release_gates")

#: Contract fields that are calibrated to one market and must never be shared.
CALIBRATED_SCALARS = ("contract_id", "product", "release_name_prefix")


def _contracts():
    return {mid: load_contract(mid) for mid in MARKETS}


# --------------------------------------------------------------------------- #
# Registry: one contract per market, no orphans in either direction.
# --------------------------------------------------------------------------- #

class TestContractRegistry:
    def test_the_single_global_contract_is_gone(self):
        """The Columbus-calibrated shared document must not come back.

        Leaving it on disk would be worse than useless: it would keep answering
        ``load`` calls that were never updated, which is exactly how the wrong
        market's numbers reached a build in the first place.
        """
        assert not (REPO_ROOT / "deploy" / "netlify" / "release_contract.json").exists()

    def test_every_market_with_verified_inventory_has_a_contract(self):
        """A release contract describes a release, so a market must have
        something to release before it needs one.

        PTF-GEOGRAPHY-NORMALIZATION-001 registered cincinnati-oh, which holds a
        121-identity census and a partition in which every identity is
        unresolved. It publishes nothing, commits no policy package, and
        therefore has no verified inventory for a contract to describe --
        ``derive_authority`` refuses outright rather than inventing an empty
        one. That is the honest-zero state the freeze anticipated, not a gap.

        Indianapolis now has eight founder-approved live records and therefore
        has its own release contract. Cincinnati remains the intentional
        contractless zero-inventory market.

        The invariant that matters is unchanged: every market that CAN release
        has a contract, and no contract exists for a market that is not
        configured.
        """
        configured = {m.market_id for m in load_markets()}
        releasable = set()
        for mid in configured:
            if mid == COLUMBUS:
                releasable.add(mid)
                continue
            path = (REPO_ROOT / "launch_packages" / "pettripfinder"
                    / ("hotel_policy_facts_%s.json" % mid))
            if not path.is_file():
                continue
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            if doc.get("published") is False:
                continue
            releasable.add(mid)
        assert releasable == set(MARKETS)
        assert set(available_market_ids()) == releasable
        assert set(available_market_ids()) <= configured

    def test_a_market_with_no_inventory_is_honestly_contractless(self):
        configured = {m.market_id for m in load_markets()}
        assert "cincinnati-oh" in configured
        assert "cincinnati-oh" not in set(available_market_ids())
        assert "indianapolis-in" in configured
        assert "indianapolis-in" in set(available_market_ids())

    def test_contract_filename_matches_declared_market(self):
        for mid in MARKETS:
            path = contract_path(mid)
            assert path.parent == RELEASE_CONTRACTS_DIR
            assert path.stem == mid
            assert json.loads(path.read_text(encoding="utf-8-sig"))["market_id"] == mid

    def test_every_contract_declares_the_current_schema(self):
        for contract in _contracts().values():
            assert contract["schema"] == CONTRACT_SCHEMA

    def test_unknown_market_fails_closed_rather_than_falling_back(self):
        """No market may borrow another's contract by being unconfigured."""
        with pytest.raises(ReleaseContractError):
            load_contract("toledo-oh")
        with pytest.raises(ReleaseContractError):
            load_contract("")


# --------------------------------------------------------------------------- #
# Agreement with each market's OWN authority.
# --------------------------------------------------------------------------- #

class TestContractAgreesWithItsOwnAuthority:
    @pytest.mark.parametrize("market_id", MARKETS)
    def test_contract_agrees_with_derived_authority(self, market_id):
        assert verify_contract(market_id) == []

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_reconciliation_matches_the_reviewed_figures(self, market_id):
        confirmed, published, no_pets, resolved, unresolved = \
            EXPECTED_RECONCILIATION[market_id]
        stated = load_contract(market_id)["reconciliation"]
        assert stated["confirmed_identities"] == confirmed
        assert stated["published_pet_friendly"] == published
        assert stated["verified_no_pets"] == no_pets
        assert stated["resolved"] == resolved
        assert stated["unresolved"] == unresolved

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_derivation_matches_the_reviewed_figures(self, market_id):
        """The derivation is checked against the same explicit figures.

        Comparing the contract to the derivation (above) would pass if both had
        drifted together. Pinning each of them to a reviewed constant is what
        makes the pair meaningful.
        """
        confirmed, published, no_pets, resolved, unresolved = \
            EXPECTED_RECONCILIATION[market_id]
        recon = derive_authority(market_id).reconciliation()
        assert recon["confirmed_identities"] == confirmed
        assert recon["published_pet_friendly"] == published
        assert recon["verified_no_pets"] == no_pets
        assert recon["resolved"] == resolved
        assert recon["unresolved"] == unresolved

    def test_verified_no_pets_is_scoped_to_the_market_that_owns_it(self):
        """31 for Cleveland, 8 for Dayton, 14 for Columbus -- never the sum.

        Counting the exclusion registry's length reported 22 verified-no-pets
        for a market that has 8, and counting every state in it reported 16 for
        a market that has 14 (two Columbus rows are a category ruling, not
        negative pet evidence).

        Dayton is 8 as of PTF-DAYTON-WORK-BROWSER-INTEGRATION-001, which added
        Best Western Celina to the seven PTF-DAYTON-CANDIDATE-PROMOTION-001 left.
        The market-scoping property is what this defends, so the number moving
        with a market's own authority is correct; the number moving because
        another market grew would not be -- and Columbus and Cleveland are
        unchanged here, which is the half of the assertion that says so.
        """
        by_market = {mid: derive_authority(mid).verified_no_pets for mid in MARKETS}
        assert by_market == {COLUMBUS: 14, CLEVELAND: 40, DAYTON: 8,
                             PITTSBURGH: 4, INDIANAPOLIS: 4, MILWAUKEE: 27,
                             ST_LOUIS: 37,
                             # PTF-LOUISVILLE-PUBLICATION-008. Every other
                             # market's number is unchanged, which is the half
                             # of this assertion that proves the scoping.
                             LOUISVILLE: 17,
                             # PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022 wrote this
                             # market's first 14. Every number above it is
                             # unchanged, which is again the half that proves
                             # the scoping.
                             GRAND_RAPIDS: 14}
        registry = json.loads(
            (REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_exclusions.json")
            .read_text(encoding="utf-8-sig"))["exclusions"]
        assert len(registry) > sum(by_market.values())

    def test_columbus_now_states_the_universe_it_could_not_before(self):
        """The absent-is-a-fact rule did its job, and is no longer needed here.

        Columbus stated `None` for as long as nothing could establish its
        universe -- absent being a fact and zero a claim. Phase C reconstructed
        the 112 identities from committed authority, so the honest answer is no
        longer silence. What must NOT happen is a market inferring 0; that
        invariant is exercised by the market below, which still has no census.
        """
        contract = load_contract(COLUMBUS)
        assert contract["identity_census"]["expected_count"] == 112
        assert contract["reconciliation"]["confirmed_identities"] == 112
        assert contract["reconciliation"]["unresolved"] == 8

    def test_a_market_without_a_census_still_refuses_to_infer_zero(self):
        """The rule itself, exercised on a synthetic market."""
        contract = load_contract(COLUMBUS)
        contract = dict(contract, identity_census=None)
        contract["reconciliation"] = dict(contract["reconciliation"],
                                          confirmed_identities=None,
                                          unresolved=None)
        problems = contract_disagreements(contract, derive_authority(COLUMBUS))
        assert any("identity_census" in p or "confirmed" in p for p in problems)

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON, PITTSBURGH, INDIANAPOLIS))
    def test_census_backed_markets_cite_their_own_census(self, market_id):
        census = load_contract(market_id)["identity_census"]
        assert market_id in census["path"]
        assert (REPO_ROOT / census["path"]).is_file()
        assert census["expected_count"] == EXPECTED_RECONCILIATION[market_id][0]

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON, PITTSBURGH))
    def test_reconciliation_cross_checks_are_declared_and_hold(self, market_id):
        """Each census-backed market cross-checks against the reconciliation
        artifact written by the work that produced its numbers."""
        checks = load_contract(market_id)["reconciliation_cross_checks"]
        assert checks, "%s declares no reconciliation cross-check" % market_id
        for check in checks:
            assert (REPO_ROOT / check["path"]).is_file()
        assert verify_contract(market_id) == []


class TestReconciliationArithmeticIsChecked:
    """A contract can be internally wrong without pointing at anything foreign."""

    def test_resolved_must_equal_published_plus_no_pets(self):
        contract = load_contract(CLEVELAND)
        contract["reconciliation"] = dict(contract["reconciliation"], resolved=26)
        problems = contract_disagreements(contract, derive_authority(CLEVELAND))
        assert any("resolved" in p for p in problems)

    def test_confirmed_minus_resolved_must_equal_unresolved(self):
        contract = load_contract(DAYTON)
        contract["reconciliation"] = dict(contract["reconciliation"],
                                          confirmed_identities=130)
        problems = contract_disagreements(contract, derive_authority(DAYTON))
        assert problems

    def test_confirmed_and_unresolved_must_be_stated_or_absent_together(self):
        """A market may not claim a universe size with nothing unaccounted for,
        nor an unresolved count with no universe to subtract it from."""
        contract = load_contract(COLUMBUS)
        contract["reconciliation"] = dict(contract["reconciliation"],
                                          confirmed_identities=102,
                                          unresolved=None)
        problems = contract_disagreements(contract, derive_authority(COLUMBUS))
        assert any("together" in p or "identity_census" in p for p in problems)

    def test_a_market_that_gains_a_census_may_not_keep_claiming_it_has_none(self):
        """Silently gaining a census would leave the contract understating the
        market, with no gate noticing."""
        contract = load_contract(CLEVELAND)
        contract["identity_census"] = None
        problems = contract_disagreements(contract, derive_authority(CLEVELAND))
        assert any("identity_census" in p for p in problems)


# --------------------------------------------------------------------------- #
# Cross-market reuse -- the regression this sprint exists for.
# --------------------------------------------------------------------------- #

class TestCrossMarketReuseIsImpossible:
    @pytest.mark.parametrize("owner,other", [
        (a, b) for a in MARKETS for b in MARKETS if a != b])
    def test_one_markets_contract_never_validates_another_markets_authority(
            self, owner, other):
        """The core anti-reuse property.

        If Columbus's contract could be satisfied by Cleveland's authority, the
        contract would not be saying anything about Columbus.
        """
        problems = contract_disagreements(load_contract(owner), derive_authority(other))
        assert problems, ("%s's contract validated against %s's authority"
                          % (owner, other))

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON))
    def test_columbus_profile_count_never_appears_in_another_contract(self, market_id):
        """88 is Columbus's inventory size and nobody else's."""
        contract = load_contract(market_id)
        assert contract["public_surface"]["public_hotel_profile_count"] != \
            COLUMBUS_PROFILE_COUNT
        assert contract["policy_package"]["expected_record_count"] != \
            COLUMBUS_PROFILE_COUNT
        assert contract["reconciliation"]["published_pet_friendly"] != \
            COLUMBUS_PROFILE_COUNT
        assert contract["routes"]["hotel_route_count"] != COLUMBUS_PROFILE_COUNT

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON))
    def test_no_market_points_at_columbus_policy_package(self, market_id):
        """Pointing a gate at another market's authority file is the quiet form
        of the same defect: the gate passes and proves nothing."""
        columbus_pkg = load_contract(COLUMBUS)["policy_package"]
        pkg = load_contract(market_id)["policy_package"]
        assert pkg["path"] != columbus_pkg["path"]
        assert pkg["expected_sha256"] != columbus_pkg["expected_sha256"]
        assert market_id in pkg["path"]

    def test_calibrated_identifiers_are_pairwise_distinct(self):
        for field in CALIBRATED_SCALARS:
            values = [load_contract(mid)[field] for mid in MARKETS]
            assert len(set(values)) == len(MARKETS), \
                "%s is shared between markets: %s" % (field, values)

    def test_package_paths_and_hashes_are_pairwise_distinct(self):
        paths = {load_contract(mid)["policy_package"]["path"] for mid in MARKETS}
        hashes = {load_contract(mid)["policy_package"]["expected_sha256"]
                  for mid in MARKETS}
        assert len(paths) == len(hashes) == len(MARKETS)

    def test_loader_refuses_a_copied_contract_that_was_not_re_scoped(
            self, tmp_path, monkeypatch):
        """Copy-paste is how the second market's contract will actually be
        written. A copy whose market_id was not changed must not load."""
        import scripts.pettripfinder.release_contracts as rc

        stolen = dict(load_contract(COLUMBUS))
        (tmp_path / "toledo-oh.json").write_text(
            json.dumps(stolen), encoding="utf-8")
        monkeypatch.setattr(rc, "RELEASE_CONTRACTS_DIR", tmp_path)
        with pytest.raises(ReleaseContractError) as exc:
            rc.load_contract("toledo-oh")
        assert "market_id" in str(exc.value)

    def test_loader_refuses_a_contract_with_the_wrong_schema(
            self, tmp_path, monkeypatch):
        import scripts.pettripfinder.release_contracts as rc

        bad = dict(load_contract(COLUMBUS), schema="ptf-something-else/9.9")
        (tmp_path / "columbus-oh.json").write_text(json.dumps(bad), encoding="utf-8")
        monkeypatch.setattr(rc, "RELEASE_CONTRACTS_DIR", tmp_path)
        with pytest.raises(ReleaseContractError):
            rc.load_contract(COLUMBUS)


# --------------------------------------------------------------------------- #
# The shared deployment target must not drift between three copies.
# --------------------------------------------------------------------------- #

class TestSharedTargetSectionsStayIdentical:
    @pytest.mark.parametrize("section", TARGET_SECTIONS)
    def test_target_section_identical_across_markets(self, section):
        """These describe the Netlify site, not a market.

        The contracts are deliberately self-contained -- no inheritance, so one
        market's edit cannot move another's expectations. The cost of that
        choice is three copies of the publish rules, and this is the check that
        keeps the copies honest.
        """
        rendered = {json.dumps(load_contract(mid)[section], sort_keys=True)
                    for mid in MARKETS}
        assert len(rendered) == 1, "%s has drifted between markets" % section

    def test_every_contract_declares_the_same_minimum_gate_set(self):
        gate_sets = [tuple(load_contract(mid)["minimum_release_gates"])
                     for mid in MARKETS]
        assert len(set(gate_sets)) == 1
        # No gate id may carry a bare number. ``route.exactly_14_hotel_profiles``
        # and ``authority.package_schema_1_1`` were both already false for the
        # market they gated, and a numeric id shared by three markets is false
        # for at least two of them by construction. A digit inside a technical
        # word (``sha256``) is not a claim about any market and is fine.
        for gate in gate_sets[0]:
            bare = [t for t in re.split(r"[^0-9a-z]+", gate) if t.isdigit()]
            assert not bare, "%s names %s" % (gate, bare)


# --------------------------------------------------------------------------- #
# A passing contract is structural, not an authorization.
# --------------------------------------------------------------------------- #

class TestPassingIsNotAuthorization:
    @pytest.mark.parametrize("market_id", MARKETS)
    def test_contract_states_what_passing_does_not_mean(self, market_id):
        block = load_contract(market_id)["deployment_authorization"]
        assert block["grants_deployment"] is False
        assert block["asserts_market_complete"] is False
        assert "not a deployment authorization" in block["means"].lower()

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON))
    def test_incomplete_markets_pass_while_stating_what_is_unresolved(self, market_id):
        """Cleveland passes with 161 unresolved and Dayton with 90.

        A release contract that could only pass on a finished market would be a
        completeness claim wearing a structural gate's name.
        """
        contract = load_contract(market_id)
        assert contract["reconciliation"]["unresolved"] > 0
        assert verify_contract(market_id) == []


# --------------------------------------------------------------------------- #
# The assembler enforces all of it.
# --------------------------------------------------------------------------- #

class TestAssemblerRefusesAForeignContract:
    def test_columbus_contract_cannot_assemble_cleveland(self, tmp_path):
        """The exact reuse that shipped: a Cleveland build reading Columbus's
        contract. It must fail BEFORE any site is generated."""
        out = tmp_path / "foreign"
        with pytest.raises(AssembleError) as exc:
            assemble("production", str(out),
                     contract=load_release_contract(COLUMBUS),
                     market=resolve_market(market_id=CLEVELAND))
        assert COLUMBUS in str(exc.value) and CLEVELAND in str(exc.value)
        assert not (out / "site").exists()
        assert not (out / "deployment_manifest.json").exists()

    @pytest.mark.parametrize("market_id", (CLEVELAND, DAYTON))
    def test_each_market_is_refused_every_other_markets_contract(
            self, market_id, tmp_path):
        for other in MARKETS:
            if other == market_id:
                continue
            with pytest.raises(AssembleError):
                assemble("production", str(tmp_path / ("x_%s" % other)),
                         contract=load_release_contract(other),
                         market=resolve_market(market_id=market_id))

    def test_a_contract_that_disagrees_with_its_authority_is_refused(self, tmp_path):
        """Editing a reviewed number without changing the authority must fail.

        This is the "fail closed if a market's contract disagrees with its
        authority" requirement, exercised from the direction that matters: the
        document is well-formed and self-consistent, and still wrong.
        """
        contract = load_release_contract(CLEVELAND)
        contract["reconciliation"] = dict(contract["reconciliation"],
                                          published_pet_friendly=20, resolved=28,
                                          unresolved=160)
        out = tmp_path / "drifted"
        with pytest.raises(AssembleError) as exc:
            assemble("production", str(out), contract=contract,
                     market=resolve_market(market_id=CLEVELAND))
        assert "authority.reconciliation_matches_market_authority" in str(exc.value)
        assert not (out / "site").exists()

    def test_a_contract_pointing_at_another_markets_package_is_refused(self, tmp_path):
        contract = load_release_contract(DAYTON)
        contract["policy_package"] = dict(
            load_release_contract(COLUMBUS)["policy_package"])
        out = tmp_path / "wrongpkg"
        with pytest.raises(AssembleError):
            assemble("production", str(out), contract=contract,
                     market=resolve_market(market_id=DAYTON))
        assert not (out / "site").exists()


# --------------------------------------------------------------------------- #
# Full per-market assembly (generation runs; module-scoped so it runs once).
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def market_bundles(tmp_path_factory):
    out = {}
    for mid in MARKETS:
        root = tmp_path_factory.mktemp("bundle_%s" % mid.replace("-", "_"))
        out[mid] = {"root": Path(root),
                    "manifest": assemble("production", str(root),
                                         market=resolve_market(market_id=mid))}
    return out


class TestEveryMarketAssembles:
    @pytest.mark.parametrize("market_id", MARKETS)
    def test_all_gates_pass(self, market_bundles, market_id):
        report = json.loads((market_bundles[market_id]["root"]
                             / "validation_report.json").read_text(encoding="utf-8"))
        assert report["all_gates_pass"] is True
        assert report["failing_gates"] == {}
        assert report["minimum_gates_missing"] == []
        assert report["gates"]["content.zero_broken_links"]["pass"] is True
        assert report["gates"]["content.quality_report_clean"]["pass"] is True

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_route_count_is_this_markets_own(self, market_bundles, market_id):
        manifest = market_bundles[market_id]["manifest"]
        assert manifest["market_id"] == market_id
        assert manifest["hotel_profile_routes"] == \
            EXPECTED_RECONCILIATION[market_id][1]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_manifest_carries_the_reconciliation_and_the_caveat(
            self, market_bundles, market_id):
        manifest = market_bundles[market_id]["manifest"]
        confirmed, published, no_pets, resolved, unresolved = \
            EXPECTED_RECONCILIATION[market_id]
        assert manifest["reconciliation"]["confirmed_identities"] == confirmed
        assert manifest["reconciliation"]["unresolved"] == unresolved
        assert manifest["release_authorization"]["grants_deployment"] is False
        assert manifest["wrote_public_or_remote"] is False
        assert set(RECONCILIATION_FIELDS) <= set(manifest["reconciliation"])

    def test_bundles_are_distinct_per_market(self, market_bundles):
        hashes = {market_bundles[mid]["manifest"]["bundle_sha256"] for mid in MARKETS}
        names = {market_bundles[mid]["manifest"]["release_name"] for mid in MARKETS}
        assert len(hashes) == len(names) == len(MARKETS)

    def test_columbus_release_name_prefix_is_preserved(self, market_bundles):
        """Columbus's live releases are identified by this prefix; a per-market
        rename would break the trail back to what is actually deployed."""
        assert market_bundles[COLUMBUS]["manifest"]["release_name"].startswith(
            "prod-005-columbus-")

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_contract_restates_an_identity_allow_list(
            self, market_bundles, market_id):
        """The package is the identity authority; a contract that duplicated the
        slugs would be a second authority nobody would remember to update."""
        raw = contract_path(market_id).read_text(encoding="utf-8")
        inventory = json.loads((market_bundles[market_id]["root"]
                                / "route_inventory.json").read_text(encoding="utf-8"))
        for slug in inventory["hotel_slugs"]:
            assert slug not in raw, "%s restates identity %s" % (market_id, slug)
