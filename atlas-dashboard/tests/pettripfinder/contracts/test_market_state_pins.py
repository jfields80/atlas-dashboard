# -*- coding: utf-8 -*-
"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- the ONE place the current-state
pins are held to the source.

``pins/market_state.json``, ``pins/deployment_state.json`` and
``pins/supersessions.json`` are explicit, reviewed expectations. Every other
suite trusts them. This module is where they are compared with the committed
release contracts, policy packages, exclusion shards, censuses, partitions, the
committed deployment manifest, the deployment records and the consumed
authorizations -- so a pin that goes stale fails HERE, once, with the market
named, instead of in nineteen modules that each restated the number.

What this deliberately does NOT do: derive a pin from the file it checks. The
expected side of every assertion is the pin; the actual side is the source.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from pettripfinder import epochs
from pettripfinder import market_state as MS
from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder.build_market_manifest import _PARTITION_FILES
from scripts.pettripfinder.hotel_exclusions import VERIFIED_NO_PETS, load_exclusions
from scripts.pettripfinder.release_contracts import (
    available_market_ids, load_contract,
)
from scripts.pettripfinder.site_data import published_facts_path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"

MARKETS = MS.market_ids()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The pin documents themselves.
# --------------------------------------------------------------------------- #

class TestPinDocuments:

    def test_market_pins_cover_exactly_the_markets_with_release_contracts(self):
        assert set(MARKETS) == set(available_market_ids())

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_pin_is_complete_and_arithmetically_consistent(self, market_id):
        pin = MS.current(market_id)
        for field in MS.MARKET_FIELDS:
            assert getattr(pin, field) is not None, (market_id, field)
        # The release contracts count OUT_OF_CURRENT_CATEGORY rows as resolved:
        # the census retains them and nothing is outstanding on them.
        assert pin.resolved == pin.pet_friendly + pin.verified_no_pets + pin.out_of_category, market_id
        assert pin.census == pin.resolved + pin.unresolved, market_id
        assert pin.profiles == pin.pet_friendly, market_id
        assert epochs.is_work_order(pin.last_moved_by), (market_id, pin.last_moved_by)

    def test_an_unpinned_market_fails_rather_than_defaulting(self):
        with pytest.raises(KeyError):
            MS.current("nowhere-xx")

    def test_pin_files_are_lf_utf8_json(self):
        for path in (MS.MARKET_STATE_PATH, MS.DEPLOYMENT_STATE_PATH,
                     epochs.SUPERSESSIONS_PATH):
            raw = path.read_bytes()
            assert b"\r\n" not in raw, path.name
            json.loads(raw.decode("utf-8"))


# --------------------------------------------------------------------------- #
# Market pins against the source.
# --------------------------------------------------------------------------- #

class TestMarketPinsAgreeWithTheSource:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_release_contract_reconciliation_matches_the_pin(self, market_id):
        pin = MS.current(market_id)
        contract = load_contract(market_id)
        rec = contract["reconciliation"]
        assert rec["confirmed_identities"] == pin.census, market_id
        assert rec["published_pet_friendly"] == pin.pet_friendly, market_id
        assert rec["verified_no_pets"] == pin.verified_no_pets, market_id
        assert rec["resolved"] == pin.resolved, market_id
        assert rec["unresolved"] == pin.unresolved, market_id
        assert contract["identity_census"]["expected_count"] == pin.census, market_id
        assert contract["policy_package"]["expected_record_count"] == pin.pet_friendly
        assert contract["public_surface"]["public_hotel_profile_count"] == pin.profiles
        assert contract["routes"]["hotel_route_count"] == pin.profiles
        assert contract["routes"]["published_corridor_route_count"] == pin.corridor_routes

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_policy_package_holds_exactly_the_pinned_records(self, market_id):
        package = _json(published_facts_path(market_id))
        assert package["market_id"] == market_id
        assert len(package["hotels"]) == MS.current(market_id).pet_friendly

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_exclusion_shard_holds_exactly_the_pinned_refusals(self, market_id):
        owned = [e for e in load_exclusions()
                 if e.get("market_id") == market_id
                 and e["exclusion_state"] == VERIFIED_NO_PETS]
        assert len(owned) == MS.current(market_id).verified_no_pets, market_id

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_census_holds_exactly_the_pinned_identities(self, market_id):
        contract = load_contract(market_id)
        census = _json(REPO_ROOT / contract["identity_census"]["path"])
        pin = MS.current(market_id)
        assert census["count"] == pin.census, market_id
        assert len(census["hotels"]) == pin.census, market_id

    @pytest.mark.parametrize("market_id", sorted(_PARTITION_FILES))
    def test_partition_counts_the_pinned_unresolved(self, market_id):
        """Unresolved is COUNTED from the market's own partition, never derived
        by subtraction alone -- the same rule the release contract states."""
        pin = MS.current(market_id)
        partition = _json(PACKAGE_DIR / _PARTITION_FILES[market_id])
        counts = partition["final_state_counts"]
        assert partition["count"] == pin.census, market_id
        assert counts.get("PUBLISHED_PET_FRIENDLY", 0) == pin.pet_friendly, market_id
        assert counts.get("VERIFIED_NO_PETS", 0) == pin.verified_no_pets, market_id
        terminal = {"PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                    "OUT_OF_CURRENT_CATEGORY"}
        unresolved = sum(n for s, n in counts.items() if s not in terminal)
        assert counts.get("OUT_OF_CURRENT_CATEGORY", 0) == pin.out_of_category, market_id
        assert unresolved == pin.unresolved, market_id


# --------------------------------------------------------------------------- #
# PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001 -- a deployment record names
# TWO orders, and they are not the same fact.
#
#   record["work_order"]                  the order that AUTHORIZED the release.
#                                         build_deployment_record() copies it
#                                         straight off the consumed
#                                         authorization -- it can be nothing
#                                         else by construction.
#   record["deployer"]["work_order"]      the order that PERFORMED the deploy.
#   record["deployer"]["authorizing_work_order"]
#                                         that deploy's own echo of the
#                                         authorizing order, written when the
#                                         two differ so neither is lost.
#   deployment_state live.deployed_by     the order that performed the CURRENT
#                                         live deploy.
#
# For the first thirty-three launches one order did both, so nothing
# distinguished them and `work_order == deployed_by` held by accident. It
# stopped holding at Fayetteville, where a host 403 split the launch and
# PTF-FAYETTEVILLE-NC-RESUME-HOST-DEPLOY-004 shipped what -002 had authorized,
# and again at Miami and Fort Lauderdale. Three records, not one.
#
# The old assertion `record["work_order"] == live.deployed_by` asked the
# authorizing order to be the deploying one. That is not a property of the
# record and never was, so the guard reported a defect that did not exist while
# checking neither fact against the document that defines it. Both are now
# checked, separately and against different documents.
# --------------------------------------------------------------------------- #

def deploying_work_order(record):
    """The order that performed ``record``'s deployment.

    ``deployer.work_order`` when the record carries it. Before that field
    existed the deploying and authorizing order were by convention the same
    one, and the top-level ``work_order`` is the only order the record names --
    so that is what it deployed under. This is a READ of the record, never a
    default: a record that is supposed to carry the field and does not is
    caught by ``record_problems``, not quietly excused here.
    """
    return (record.get("deployer") or {}).get("work_order") or record.get("work_order")


def authorizing_work_order(record):
    """The order that authorized ``record``'s release, as the record states it."""
    return record.get("work_order")


def first_record_naming_its_deployer(records):
    """The deploy at which ``deployer.work_order`` entered the schema.

    Derived, not pinned to a market name: the earliest record that carries the
    field. Every record from there on owes it -- that is what stops the field
    being silently dropped by a future deploy -- and no record before it does.
    """
    for record in sorted(records, key=lambda r: r["deployed_at"]):
        if (record.get("deployer") or {}).get("work_order"):
            return record
    return None


def record_problems(records, authorizations):
    """Every way the committed records fail the two-order contract.

    ``authorizations`` is keyed by authorization id. Both sides of every
    comparison come from a different document: the record from
    ``deployment_records``, the order it claims from ``deployment_authorizations``.
    """
    problems = []
    by_id = dict(authorizations)
    ordered = sorted(records, key=lambda r: r["deployed_at"])
    first_named = first_record_naming_its_deployer(ordered)
    owes_deployer = False

    for record in ordered:
        rid = record["deployment_record_id"]
        deployer = record.get("deployer") or {}

        # 1 -- the authorizing order is the authorization's own.
        auth = by_id.get(record.get("authorization_id"))
        if auth is None:
            problems.append(
                "%s: authorization %r is unreachable, so the order it was "
                "released under cannot be confirmed"
                % (rid, record.get("authorization_id")))
        elif authorizing_work_order(record) != auth.get("work_order"):
            problems.append(
                "%s: work_order is %r but authorization %s was signed by %r; "
                "the record's work_order IS the authorizing order"
                % (rid, authorizing_work_order(record), auth["authorization_id"],
                   auth.get("work_order")))
        if not epochs.is_work_order(authorizing_work_order(record)):
            problems.append("%s: work_order %r does not name a work order"
                            % (rid, authorizing_work_order(record)))

        # 2 -- the deploying order, once the schema carries it, stays carried.
        if first_named is not None and record is first_named:
            owes_deployer = True
        if owes_deployer and not deployer.get("work_order"):
            problems.append(
                "%s: deployed at %s, after %s introduced deployer.work_order, "
                "but names no deploying order"
                % (rid, record["deployed_at"], first_named["deployment_record_id"]))
        if deployer.get("work_order") and \
                not epochs.is_work_order(deployer["work_order"]):
            problems.append("%s: deployer.work_order %r does not name a work order"
                            % (rid, deployer["work_order"]))

        # 3 -- and the two are never conflated. Where a record echoes the
        #      authorizing order inside its deployer block it must echo the
        #      real one, and where the two orders differ the record must say
        #      so explicitly rather than leave the difference to be inferred.
        echo = deployer.get("authorizing_work_order")
        if echo is not None and echo != authorizing_work_order(record):
            problems.append(
                "%s: deployer.authorizing_work_order is %r but the record was "
                "released under %r"
                % (rid, echo, authorizing_work_order(record)))
        if deployer.get("work_order") and \
                deployer["work_order"] != authorizing_work_order(record) and \
                echo is None:
            problems.append(
                "%s: deployed by %r under a different authorizing order %r "
                "without recording deployer.authorizing_work_order"
                % (rid, deployer["work_order"], authorizing_work_order(record)))
    return problems


def live_lineage_problems(live, records, authorizations):
    """Every way the live pin fails to describe the deployment production runs.

    Identity, not arithmetic: the latest record by deployment time IS the live
    one, it carries the live bundle and site, and its two orders are the two
    the pin names.
    """
    problems = []
    by_record_id = {r["deployment_record_id"]: r for r in records}
    record = by_record_id.get(live.deployment_record_id)
    if record is None:
        problems.append("the live pin names deployment record %r, which does not exist"
                        % live.deployment_record_id)
        return problems

    latest = max(records, key=lambda r: r["deployed_at"])
    if latest["deployment_record_id"] != record["deployment_record_id"]:
        problems.append(
            "the latest deployment record is %s (%s) but the live pin names %s"
            % (latest["deployment_record_id"], latest["deployed_at"],
               record["deployment_record_id"]))

    if record["deployment_id"] != live.deploy_id:
        problems.append("live deploy id is %r; record %s deployed %r"
                        % (live.deploy_id, record["deployment_record_id"],
                           record["deployment_id"]))
    if record["bundle_sha256"] != live.bundle_sha256:
        problems.append("live bundle is %r; record %s shipped %r"
                        % (live.bundle_sha256, record["deployment_record_id"],
                           record["bundle_sha256"]))
    if record["sitemap_sha256"] != live.sitemap_sha256:
        problems.append("live sitemap is %r; record %s shipped %r"
                        % (live.sitemap_sha256, record["deployment_record_id"],
                           record["sitemap_sha256"]))
    if record["target_site"] != LIVE_TARGET_SITE:
        problems.append("record %s deployed to site %r, not %r"
                        % (record["deployment_record_id"], record["target_site"],
                           LIVE_TARGET_SITE))

    # The two orders, each against the document that defines it.
    if deploying_work_order(record) != live.deployed_by:
        problems.append(
            "live.deployed_by is %r but deployment record %s was deployed by %r"
            % (live.deployed_by, record["deployment_record_id"],
               deploying_work_order(record)))
    auth = {a["authorization_id"]: a for a in authorizations}.get(live.authorization_id)
    if auth is None:
        problems.append("the live authorization %r is unreachable"
                        % live.authorization_id)
    elif authorizing_work_order(record) != auth.get("work_order"):
        problems.append(
            "the live record was released under %r but its authorization %s was "
            "signed by %r"
            % (authorizing_work_order(record), auth["authorization_id"],
               auth.get("work_order")))
    if not epochs.is_work_order(live.deployed_by):
        problems.append("live.deployed_by %r does not name a work order"
                        % live.deployed_by)
    return problems


#: Every committed record deployed here, so the live one deploying anywhere
#: else is a finding rather than a passing comparison against itself.
LIVE_TARGET_SITE = "pettripfinder-prod"


# --------------------------------------------------------------------------- #
# Deployment pins against the manifest and the records.
# --------------------------------------------------------------------------- #

class TestDeploymentPinsAgreeWithTheSource:

    def test_live_block_is_the_latest_deployment_record(self):
        live = MS.live()
        record = DA._read_json(DA.record_path(live.deployment_record_id))
        assert record["deployment_id"] == live.deploy_id
        assert record["authorization_id"] == live.authorization_id
        # `record["work_order"]` is the AUTHORIZING order and `live.deployed_by`
        # is the DEPLOYING one; they are different facts and are allowed to
        # differ. Comparing them here conflated the two and failed for three
        # launches. Each is now held to the document that actually defines it,
        # by TestTheDeploymentRecordSeparatesAuthorizingFromDeploying below.
        assert deploying_work_order(record) == live.deployed_by
        assert record["source_commit"] == live.source_commit
        assert record["bundle_sha256"] == live.bundle_sha256
        assert record["sitemap_sha256"] == live.sitemap_sha256
        assert record["previous_deployment_id"] == live.previous_deploy_id
        assert record["rollback_target"] == live.rollback_target
        assert record["participating_markets"] == list(live.participating_markets)
        assert record["profile_counts"] == dict(live.profile_counts)
        assert record["total_profiles"] == live.total_profiles
        assert record["sitemap_route_count"] == live.sitemap_route_count
        assert record["final_status"] == DA.DEPLOYED
        # And it IS the latest: no record deployed later names another id.
        latest = max(DA.list_records(), key=lambda r: r["deployed_at"])
        assert latest["deployment_id"] == live.deploy_id

    def test_live_profile_counts_are_the_market_pins(self):
        """What production serves is what the market pins say -- for every
        market that has not moved since the live deploy.

        PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005 scoped this rather than
        relaxing it. A promotion order moves SOURCE and deploys nothing, so
        between that order and the deployment that ships it the two numbers are
        SUPPOSED to differ for exactly one market. Asserting equality for all
        of them made a correct source-ahead state read as corruption.

        The exemption is not a blanket: a market is excused only if the
        supersessions pin NAMES it against the live authorization, together
        with the work order that moved it. Every market that is not named is
        still held to the live count exactly as before, and a market that
        drifts without being named still fails.
        """
        live = MS.live()
        assert sum(live.profile_counts.values()) == live.total_profiles
        moved = epochs.moved_by_later_work(live.authorization_id)
        for market_id, count in live.profile_counts.items():
            if market_id in moved:
                # Named as moved: it must actually have moved, or the
                # exemption is hiding nothing and should not be claimed.
                assert MS.current(market_id).profiles != count, (
                    "%s is named as moved by %s but still matches the live count"
                    % (market_id, moved[market_id]))
                continue
            assert count == MS.current(market_id).profiles, market_id

    def test_committed_manifest_describes_the_live_deploy(self):
        """The committed manifest describes what production serves. An
        application order moves SOURCE, never this, until a deployment ships."""
        live = MS.live()
        manifest = GD.load_manifest()
        assert manifest["bundle_sha256"] == live.bundle_sha256
        assert manifest["sitemap_sha256"] == live.sitemap_sha256
        assert manifest["total_published_profiles"] == live.total_profiles
        assert manifest["sitemap_route_count"] == live.sitemap_route_count
        assert manifest["total_html_pages"] == live.total_html_pages
        assert manifest["total_files"] == live.total_files
        assert manifest["source_commit"] == live.source_commit

    def test_source_block_names_its_relation_to_production(self):
        live, source = MS.live(), MS.source_assembly()
        assert source.ahead_of_production in (True, False)
        if source.ahead_of_production:
            assert epochs.is_work_order(source.moved_by), source.moved_by
            assert source.bundle_sha256 != live.bundle_sha256
        else:
            assert source.moved_by is None
            assert source.bundle_sha256 == live.bundle_sha256
            assert source.sitemap_sha256 == live.sitemap_sha256
            assert source.total_profiles == live.total_profiles
            assert source.sitemap_route_count == live.sitemap_route_count
            assert source.profile_counts == live.profile_counts
        assert sum(source.profile_counts.values()) == source.total_profiles
        for market_id, count in source.profile_counts.items():
            assert count == MS.current(market_id).profiles, market_id


# --------------------------------------------------------------------------- #
# Supersessions: consumed authorizations and what later work moved.
# --------------------------------------------------------------------------- #

class TestSupersessionRegistry:

    def _registry(self):
        return epochs.supersession_registry()["authorizations"]

    def test_every_listed_authorization_exists_and_was_consumed(self):
        for auth_id, entry in self._registry().items():
            auth = DA.load_authorization(auth_id)
            assert auth["work_order"] == entry["work_order"], auth_id
            assert auth["authorization_status"] in (DA.DEPLOYED, DA.SUPERSEDED), auth_id

    def test_moved_markets_really_differ_from_what_was_authorized(self):
        """The registry may not over-claim: a market listed as moved must have
        a contract whose bytes no longer match the authorization's pin."""
        for auth_id in self._registry():
            auth = DA.load_authorization(auth_id)
            pinned = {row["market_id"]: row for row in auth["release_contracts"]}
            for market_id, order in epochs.moved_by_later_work(auth_id).items():
                assert epochs.is_work_order(order), (auth_id, market_id)
                if market_id not in pinned:
                    # Registered AFTER this authorization was signed: it moved
                    # the participation record, not a contract the
                    # authorization ever bound. It must not have participated.
                    assert market_id not in auth["participating_markets"], (
                        auth_id, market_id)
                    continue
                row = pinned[market_id]
                assert row["sha256"] != DA._sha256_file(REPO_ROOT / row["path"]), (
                    "%s: %s is listed as moved by %s but its contract still "
                    "matches the authorization" % (auth_id, market_id, order))

    def test_unmoved_markets_still_bind_exactly(self):
        """And it may not under-claim: everything later work did not touch
        still binds, so the historical authorization stays specific evidence."""
        for auth_id in self._registry():
            auth = DA.load_authorization(auth_id)
            moved = epochs.markets_moved_since(auth_id)
            for row in auth["release_contracts"]:
                if row["market_id"] in moved:
                    continue
                assert row["sha256"] == DA._sha256_file(REPO_ROOT / row["path"]), (
                    auth_id, row["market_id"])

    def test_the_live_authorization_has_nothing_moved(self):
        """What production serves was authorized against what source holds,
        so the live authorization binds every market -- until the next
        application order moves one, at which point that order lists it."""
        live = MS.live()
        if not MS.source_assembly().ahead_of_production:
            assert epochs.moved_by_later_work(live.authorization_id) == {}

    def test_an_unregistered_authorization_binds_everything(self):
        with pytest.raises(KeyError):
            epochs.moved_by_later_work("ptf-auth-000-000000000000")

    def test_declared_supersessions_all_name_a_work_order(self):
        for entry in epochs.DECLARED_SUPERSESSIONS:
            assert epochs.is_work_order(entry.superseded_by), entry
            assert entry.what, entry


# --------------------------------------------------------------------------- #
# PTF-SUPERSESSIONS-LINEAGE-REPAIR-001 -- the registry is a CHAIN, and it has to
# reach the authorization production is serving under.
#
# The registry went nineteen launches without an entry. Nothing said so: the
# three tests above iterate what IS listed, and the two that ask about the LIVE
# authorization raised KeyError instead of reporting a stale pin, so
# `test_live_profile_counts_are_the_market_pins` and
# `test_the_live_authorization_binds_every_market_exactly` errored out without
# checking a single market. A fail-closed lookup is right -- it is what stops an
# unlisted authorization being silently excused -- but nothing downstream of it
# named the real defect, which is that the CHAIN had stopped being extended.
#
# So the chain itself is now the pin: what the registry must list is derivable
# from the committed deployment records, and `chain_problems` says exactly how a
# registry differs from that. The positive tests below require it to be empty;
# the negative tests hand it, and the real guards above, registries that are
# wrong in each way that matters and require each one to be caught.
# --------------------------------------------------------------------------- #

#: The seed. PTF-FACTORY-THROUGHPUT-HARDENING-001 created the registry with the
#: first multi-market authorization and the one live on the day it was written.
#: The seven authorizations production consumed between those two predate the
#: registry and were never listed. That gap is historical and closed: from
#: CHAIN_STARTS_AT onward every consumed authorization must be listed, in the
#: order production consumed them, ending at the live one.
PRE_REGISTRY_ENTRIES = ("ptf-auth-047-a324b1bf5023",)
CHAIN_STARTS_AT = "ptf-auth-003-de669c40d811"

#: The prose a registry entry uses to say it is the one production serves under.
CURRENT_MARKER = "The CURRENT live authorization"


def deployment_chain():
    """Consumed authorizations, in the order production consumed them.

    Derived from the deployment records rather than from the registry, so the
    two sides of every comparison below come from different documents.
    """
    records = {r["authorization_id"]: r for r in DA.list_records()}
    return [auth_id for _, auth_id in
            sorted((records[a["authorization_id"]]["deployed_at"], a["authorization_id"])
                   for a in DA.list_authorizations()
                   if a["authorization_id"] in records)]


def expected_chain(live_authorization_id):
    """Exactly the entries the registry owes, in order."""
    chain = deployment_chain()
    listed = chain[chain.index(CHAIN_STARTS_AT):chain.index(live_authorization_id) + 1]
    return list(PRE_REGISTRY_ENTRIES) + listed


def chain_problems(registry, live_authorization_id):
    """Every way ``registry`` fails to describe production's own lineage."""
    problems = []
    keys = list(registry)
    if live_authorization_id not in registry:
        problems.append("the live authorization %s is not listed; the profile-pin and "
                        "contract-binding guards cannot run" % live_authorization_id)
    expected = expected_chain(live_authorization_id)
    if keys != expected:
        missing = [k for k in expected if k not in keys]
        extra = [k for k in keys if k not in expected]
        if missing:
            problems.append("consumed authorizations are missing: %s" % ", ".join(missing))
        if extra:
            problems.append("listed but never consumed in this chain: %s" % ", ".join(extra))
        if not missing and not extra:
            problems.append("listed out of the order production consumed them: %s"
                            % ", ".join(keys))
    current = [k for k, e in registry.items() if CURRENT_MARKER in (e.get("note") or "")]
    if current != [live_authorization_id]:
        problems.append("%r describes %s as current; production serves under %s"
                        % (CURRENT_MARKER, ", ".join(current) or "nothing",
                           live_authorization_id))
    return problems


class TestTheSupersessionChainReachesProduction:
    """The repair's own contract: the registry stays current, or says so."""

    def test_the_chain_is_complete_in_order_and_ends_at_the_live_authorization(self):
        registry = epochs.supersession_registry()["authorizations"]
        assert chain_problems(registry, MS.live().authorization_id) == []

    def test_the_live_authorization_resolves_and_binds_every_live_market(self):
        """The two guards the missing entry disabled, asserted as coverage."""
        live = MS.live()
        moved = epochs.moved_by_later_work(live.authorization_id)
        checked = [m for m in live.profile_counts if m not in moved]
        assert len(checked) == len(live.profile_counts), moved
        assert len(checked) == len(live.participating_markets)

    def test_the_registry_is_reviewed_by_a_work_order(self):
        assert epochs.is_work_order(epochs.supersession_registry()["reviewed_by"])

    def test_no_withheld_market_is_treated_as_live_or_excused(self):
        """A market the founder has not authorized serves nothing, so it cannot
        appear in the live block and cannot be excused as having moved out from
        under the authorization that serves production."""
        from scripts.pettripfinder import launch_participation as LP

        live = MS.live()
        moved = epochs.moved_by_later_work(live.authorization_id)
        withheld = [m for m in MS.market_ids()
                    if LP.launch_status(m) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH]
        assert withheld, "a guard about withheld markets needs one to exist"
        for market_id in withheld:
            assert market_id not in live.participating_markets, market_id
            assert market_id not in live.profile_counts, market_id
            assert market_id not in moved, market_id


class TestTheSupersessionContractFailsClosed:
    """Hand the real guards a registry that is wrong, and require the failure.

    Every fixture here is a deep copy written to ``tmp_path``. The committed
    pins are never mutated; the module path under test is pointed at the copy
    for the duration of one test.
    """

    @staticmethod
    def _install(monkeypatch, tmp_path, doc):
        path = tmp_path / "supersessions.json"
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        monkeypatch.setattr(epochs, "SUPERSESSIONS_PATH", path)
        return path

    def _doc(self):
        return json.loads(epochs.SUPERSESSIONS_PATH.read_text(encoding="utf-8"))

    # 1 -- the defect this order repaired.
    def test_a_registry_that_forgets_the_live_authorization_is_caught(
            self, monkeypatch, tmp_path):
        live_id = MS.live().authorization_id
        doc = self._doc()
        doc["authorizations"].pop(live_id)
        self._install(monkeypatch, tmp_path, doc)
        problems = chain_problems(epochs.supersession_registry()["authorizations"], live_id)
        assert any("is not listed" in p for p in problems), problems
        assert any("missing" in p for p in problems), problems

    # 3 -- and the lookup itself still refuses to invent an answer.
    def test_a_missing_moved_by_later_work_lookup_raises_rather_than_defaulting(
            self, monkeypatch, tmp_path):
        live_id = MS.live().authorization_id
        doc = self._doc()
        doc["authorizations"].pop(live_id)
        self._install(monkeypatch, tmp_path, doc)
        with pytest.raises(KeyError):
            epochs.moved_by_later_work(live_id)

    # 2 -- a reviewer that is not a work order.
    def test_a_reviewed_by_that_names_no_work_order_is_caught(
            self, monkeypatch, tmp_path):
        doc = self._doc()
        doc["reviewed_by"] = "somebody, last week"
        self._install(monkeypatch, tmp_path, doc)
        assert not epochs.is_work_order(epochs.supersession_registry()["reviewed_by"])

    # 2 -- and a mover that is not one either.
    def test_a_mover_that_names_no_work_order_is_caught(self, monkeypatch, tmp_path):
        live_id = MS.live().authorization_id
        doc = self._doc()
        doc["authorizations"][live_id]["moved_by_later_work"] = {"miami-fl": "later work"}
        self._install(monkeypatch, tmp_path, doc)
        with pytest.raises(ValueError):
            epochs.moved_by_later_work(live_id)

    # 4 -- chronology that runs backwards.
    def test_a_chain_listed_out_of_deployment_order_is_caught(
            self, monkeypatch, tmp_path):
        live_id = MS.live().authorization_id
        doc = self._doc()
        entries = list(doc["authorizations"].items())
        entries[-1], entries[-2] = entries[-2], entries[-1]
        doc["authorizations"] = dict(entries)
        self._install(monkeypatch, tmp_path, doc)
        problems = chain_problems(epochs.supersession_registry()["authorizations"], live_id)
        assert any("out of the order" in p for p in problems), problems

    # 5 -- deployment lineage and supersession lineage disagreeing.
    def test_an_entry_for_an_authorization_that_does_not_exist_is_caught(
            self, monkeypatch, tmp_path):
        doc = self._doc()
        doc["authorizations"]["ptf-auth-000-000000000000"] = {
            "work_order": "PTF-NO-SUCH-ORDER-001", "moved_by_later_work": {}}
        self._install(monkeypatch, tmp_path, doc)
        with pytest.raises(Exception):
            TestSupersessionRegistry().test_every_listed_authorization_exists_and_was_consumed()

    def test_an_entry_whose_work_order_is_not_the_authorizations_is_caught(
            self, monkeypatch, tmp_path):
        live_id = MS.live().authorization_id
        doc = self._doc()
        doc["authorizations"][live_id]["work_order"] = "PTF-SOME-OTHER-ORDER-001"
        self._install(monkeypatch, tmp_path, doc)
        with pytest.raises(AssertionError):
            TestSupersessionRegistry().test_every_listed_authorization_exists_and_was_consumed()

    def test_a_market_excused_without_having_moved_is_caught(
            self, monkeypatch, tmp_path):
        """The exemption may not be claimed for a market that still binds."""
        live_id = MS.live().authorization_id
        doc = self._doc()
        doc["authorizations"][live_id]["moved_by_later_work"] = {
            "miami-fl": "PTF-SUPERSESSIONS-LINEAGE-REPAIR-001"}
        self._install(monkeypatch, tmp_path, doc)
        with pytest.raises(AssertionError):
            TestSupersessionRegistry().test_moved_markets_really_differ_from_what_was_authorized()

    # 6 -- a live market whose pin cannot be reached.
    def test_a_live_market_with_no_pin_fails_rather_than_defaulting(
            self, monkeypatch, tmp_path):
        live = MS.live()
        absent = sorted(live.profile_counts)[0]
        doc = json.loads(MS.MARKET_STATE_PATH.read_text(encoding="utf-8"))
        doc["markets"].pop(absent)
        path = tmp_path / "market_state.json"
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        monkeypatch.setattr(MS, "MARKET_STATE_PATH", path)
        with pytest.raises(KeyError):
            TestDeploymentPinsAgreeWithTheSource().test_live_profile_counts_are_the_market_pins()

    # 7 -- a withheld market carried into the live set.
    def test_a_withheld_market_named_as_live_is_caught(self, monkeypatch, tmp_path):
        from scripts.pettripfinder import launch_participation as LP

        withheld = next(m for m in MS.market_ids()
                        if LP.launch_status(m) != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        assert withheld not in MS.live().participating_markets
        doc = json.loads(MS.DEPLOYMENT_STATE_PATH.read_text(encoding="utf-8"))
        doc["live"]["participating_markets"].append(withheld)
        doc["live"]["profile_counts"][withheld] = MS.current(withheld).profiles
        path = tmp_path / "deployment_state.json"
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        monkeypatch.setattr(MS, "DEPLOYMENT_STATE_PATH", path)
        assert withheld in MS.live().participating_markets
        with pytest.raises(AssertionError):
            TestTheSupersessionChainReachesProduction()\
                .test_no_withheld_market_is_treated_as_live_or_excused()


# --------------------------------------------------------------------------- #
# PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001 -- the two-order contract.
#
# The positive tests hold every committed record to it. The negative tests hand
# the same guards records that are wrong in each way that matters and require
# each one to be caught, so the guards cannot pass by asserting nothing.
#
# Every fixture below is a deep copy of committed bytes, mutated in memory and
# never written back. No committed deployment record, authorization or pin is
# modified by this module.
# --------------------------------------------------------------------------- #

class TestTheDeploymentRecordSeparatesAuthorizingFromDeploying:

    def _records(self):
        return DA.list_records()

    def _authorizations(self):
        return {a["authorization_id"]: a for a in DA.list_authorizations()}

    def test_every_record_was_released_under_its_authorizations_own_order(self):
        """Contract 1: ``work_order`` IS the authorizing order, for all of them.

        That is what ``build_deployment_record`` writes -- it copies
        ``auth["work_order"]`` -- so a record disagreeing with the
        authorization it names was not built by the factory.
        """
        records, auths = self._records(), self._authorizations()
        assert records, "a contract about deployment records needs some"
        disagreeing = [
            r["deployment_record_id"] for r in records
            if authorizing_work_order(r) != auths[r["authorization_id"]]["work_order"]
        ]
        assert disagreeing == [], disagreeing

    def test_every_record_names_a_reachable_authorization(self):
        records, auths = self._records(), self._authorizations()
        unreachable = [r["deployment_record_id"] for r in records
                       if r.get("authorization_id") not in auths]
        assert unreachable == [], unreachable

    def test_every_record_since_the_field_existed_names_its_deploying_order(self):
        """Contract 2: once a record carried ``deployer.work_order``, every
        later one does. Derived from the records, so no market is named."""
        records = self._records()
        first = first_record_naming_its_deployer(records)
        assert first is not None, "no record names its deploying order"
        later = [r for r in records if r["deployed_at"] >= first["deployed_at"]]
        silent = [r["deployment_record_id"] for r in later
                  if not (r.get("deployer") or {}).get("work_order")]
        assert silent == [], silent

    def test_the_two_orders_are_allowed_to_differ_and_some_really_do(self):
        """Contract 5, stated positively: these are two facts, not one.

        If no committed record ever separated them the repaired guard would be
        indistinguishable from the broken one and this module would prove
        nothing. Production really does hold releases whose deploying order is
        not the order that authorized them -- and each records BOTH, so neither
        fact was lost when they diverged.
        """
        diverged = [r for r in self._records()
                    if (r.get("deployer") or {}).get("work_order")
                    and r["deployer"]["work_order"] != authorizing_work_order(r)]
        assert diverged, (
            "no record separates the authorizing from the deploying order; "
            "the repaired guard would be untested")
        for record in diverged:
            assert record["deployer"]["authorizing_work_order"] == \
                authorizing_work_order(record), record["deployment_record_id"]
            assert epochs.is_work_order(record["deployer"]["work_order"])

    def test_the_committed_records_satisfy_the_whole_contract(self):
        assert record_problems(self._records(), self._authorizations()) == []

    def test_the_live_pin_describes_the_deployment_production_runs(self):
        """Contracts 3 and 4: the live pin's lineage, identity and both orders."""
        assert live_lineage_problems(
            MS.live(), self._records(), DA.list_authorizations()) == []

    def test_the_live_pins_two_orders_are_each_the_record_they_come_from(self):
        """Named explicitly, because this is the pair the old guard conflated."""
        live = MS.live()
        record = DA._read_json(DA.record_path(live.deployment_record_id))
        auth = DA.load_authorization(live.authorization_id)
        assert deploying_work_order(record) == live.deployed_by
        assert authorizing_work_order(record) == auth["work_order"]
        assert epochs.is_work_order(live.deployed_by)
        assert epochs.is_work_order(auth["work_order"])


class TestTheTwoOrderContractFailsClosed:
    """Each way a record or pin can be wrong, and the guard that catches it."""

    @staticmethod
    def _copy(records):
        return [json.loads(json.dumps(r)) for r in records]

    def _fixture(self):
        """A deep copy of the committed records and authorizations."""
        records = self._copy(DA.list_records())
        auths = {a["authorization_id"]: json.loads(json.dumps(a))
                 for a in DA.list_authorizations()}
        return records, auths

    @staticmethod
    def _live_record(records):
        return max(records, key=lambda r: r["deployed_at"])

    # 1 -- the record's work_order disagrees with its authorization.
    def test_a_record_that_disagrees_with_its_authorization_is_caught(self):
        records, auths = self._fixture()
        victim = self._live_record(records)
        victim["work_order"] = "PTF-SOME-OTHER-ORDER-001"
        problems = record_problems(records, auths)
        assert any("the record's work_order IS the authorizing order" in p
                   for p in problems), problems
        assert any(victim["deployment_record_id"] in p for p in problems), problems

    def test_a_disagreeing_record_also_fails_the_positive_guard(self, monkeypatch):
        records = self._copy(DA.list_records())
        self._live_record(records)["work_order"] = "PTF-SOME-OTHER-ORDER-001"
        monkeypatch.setattr(DA, "list_records", lambda: records)
        with pytest.raises(AssertionError):
            TestTheDeploymentRecordSeparatesAuthorizingFromDeploying()\
                .test_every_record_was_released_under_its_authorizations_own_order()

    # 2 -- deployer.work_order missing after the field existed.
    def test_a_record_that_drops_its_deploying_order_is_caught(self):
        records, auths = self._fixture()
        self._live_record(records)["deployer"].pop("work_order")
        problems = record_problems(records, auths)
        assert any("names no deploying order" in p for p in problems), problems

    def test_a_dropped_deploying_order_also_fails_the_positive_guard(self, monkeypatch):
        records = self._copy(DA.list_records())
        self._live_record(records)["deployer"].pop("work_order")
        monkeypatch.setattr(DA, "list_records", lambda: records)
        with pytest.raises(AssertionError):
            TestTheDeploymentRecordSeparatesAuthorizingFromDeploying()\
                .test_every_record_since_the_field_existed_names_its_deploying_order()

    # 3 -- deployer.work_order is wrong: not an order at all, or it diverges
    #      while the record hides the divergence, or it echoes the wrong
    #      authorizing order.
    def test_a_deploying_order_that_is_not_a_work_order_is_caught(self):
        records, auths = self._fixture()
        self._live_record(records)["deployer"]["work_order"] = "deployed by hand"
        problems = record_problems(records, auths)
        assert any("deployer.work_order" in p and "does not name a work order" in p
                   for p in problems), problems

    def test_a_divergence_recorded_with_the_wrong_authorizing_order_is_caught(self):
        records, auths = self._fixture()
        victim = self._live_record(records)
        victim["deployer"]["authorizing_work_order"] = "PTF-NOT-THE-AUTHORIZER-001"
        problems = record_problems(records, auths)
        assert any("but the record was released under" in p for p in problems), problems

    def test_an_undeclared_divergence_is_caught(self):
        records, auths = self._fixture()
        victim = self._live_record(records)
        victim["deployer"].pop("authorizing_work_order", None)
        victim["deployer"]["work_order"] = "PTF-SOME-DEPLOYING-ORDER-009"
        problems = record_problems(records, auths)
        assert any("without recording deployer.authorizing_work_order" in p
                   for p in problems), problems

    # 4 -- live.deployed_by points at a different deployment action.
    def test_a_live_deployed_by_naming_another_action_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(MS.live(), deployed_by="PTF-A-DIFFERENT-DEPLOY-002")
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("live.deployed_by is" in p for p in problems), problems

    def test_a_live_deployed_by_that_is_not_a_work_order_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(MS.live(), deployed_by="whoever ran it")
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("live.deployed_by" in p and "does not name a work order" in p
                   for p in problems), problems

    def test_the_repaired_live_guard_catches_a_moved_deployed_by(self, monkeypatch):
        """And the guard the old assertion lived in still fails closed."""
        doc = json.loads(MS.DEPLOYMENT_STATE_PATH.read_text(encoding="utf-8"))
        doc["live"]["deployed_by"] = "PTF-A-DIFFERENT-DEPLOY-002"
        monkeypatch.setattr(MS, "deployment_state_document", lambda: doc)
        with pytest.raises(AssertionError):
            TestDeploymentPinsAgreeWithTheSource()\
                .test_live_block_is_the_latest_deployment_record()

    def test_the_repaired_live_guard_still_accepts_the_committed_pin(self):
        """It is repaired, not weakened: unmutated, it passes on the real pin."""
        TestDeploymentPinsAgreeWithTheSource()\
            .test_live_block_is_the_latest_deployment_record()

    # 5 -- the latest record is not the live one.
    def test_a_latest_record_that_is_not_the_live_one_is_caught(self):
        records, auths = self._fixture()
        newer = json.loads(json.dumps(self._live_record(records)))
        newer["deployment_record_id"] = "ptf-deploy-nowhere-001-ffffffffffffffffffffffff"
        newer["deployment_id"] = "ffffffffffffffffffffffff"
        newer["deployed_at"] = "2099-01-01T00:00:00Z"
        records.append(newer)
        problems = live_lineage_problems(MS.live(), records, list(auths.values()))
        assert any("the latest deployment record is" in p for p in problems), problems

    def test_a_live_pin_naming_no_record_at_all_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(
            MS.live(), deployment_record_id="ptf-deploy-nowhere-001")
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("which does not exist" in p for p in problems), problems

    def test_a_live_deploy_id_the_record_never_shipped_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(MS.live(), deploy_id="ffffffffffffffffffffffff")
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("live deploy id is" in p for p in problems), problems

    # 6 -- bundle / sitemap / site identity differs.
    def test_a_live_bundle_that_the_record_never_shipped_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(MS.live(), bundle_sha256="00" * 32)
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("live bundle is" in p for p in problems), problems

    def test_a_live_sitemap_that_the_record_never_shipped_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(MS.live(), sitemap_sha256="00" * 32)
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("live sitemap is" in p for p in problems), problems

    def test_a_record_deployed_to_another_site_is_caught(self):
        records, auths = self._fixture()
        self._live_record(records)["target_site"] = "pettripfinder-staging"
        problems = live_lineage_problems(MS.live(), records, list(auths.values()))
        assert any("not %r" % LIVE_TARGET_SITE in p for p in problems), problems

    # 7 -- authorization lineage unreachable.
    def test_a_record_whose_authorization_is_unreachable_is_caught(self):
        records, auths = self._fixture()
        self._live_record(records)["authorization_id"] = "ptf-auth-000-000000000000"
        problems = record_problems(records, auths)
        assert any("is unreachable" in p for p in problems), problems

    def test_a_live_authorization_that_is_unreachable_is_caught(self):
        records, auths = self._fixture()
        moved = dataclasses.replace(
            MS.live(), authorization_id="ptf-auth-000-000000000000")
        problems = live_lineage_problems(moved, records, list(auths.values()))
        assert any("the live authorization" in p and "unreachable" in p
                   for p in problems), problems

    def test_an_unreachable_authorization_also_fails_the_positive_guard(
            self, monkeypatch):
        records = self._copy(DA.list_records())
        self._live_record(records)["authorization_id"] = "ptf-auth-000-000000000000"
        monkeypatch.setattr(DA, "list_records", lambda: records)
        with pytest.raises(AssertionError):
            TestTheDeploymentRecordSeparatesAuthorizingFromDeploying()\
                .test_every_record_names_a_reachable_authorization()

    # 8 -- and the guards are not vacuous: unmutated, they report nothing.
    def test_the_unmutated_fixture_reports_no_problems(self):
        records, auths = self._fixture()
        assert record_problems(records, auths) == []
        assert live_lineage_problems(MS.live(), records, list(auths.values())) == []

    def test_the_committed_records_are_not_touched_by_these_fixtures(self):
        """A fixture is a copy. Whatever the tests above did to theirs, the
        bytes on disk still say what the live pin was built from."""
        live = MS.live()
        on_disk = DA._read_json(DA.record_path(live.deployment_record_id))
        assert on_disk["bundle_sha256"] == live.bundle_sha256
        assert on_disk["deployment_id"] == live.deploy_id
        assert on_disk["work_order"] == \
            DA.load_authorization(live.authorization_id)["work_order"]
