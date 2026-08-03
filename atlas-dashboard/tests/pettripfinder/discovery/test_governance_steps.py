"""WO-1A Steps 6-11 -- idempotency, supersession, lifecycle, URL revalidation,
provider terms, and fail-closed robots.

Grouped in one module because they are one governance layer around an existing,
frozen discovery engine: each enforces a founder decision (FD-2/4/5/6/1) and
none changes how discovery finds or merges anything.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import history, idempotency, lifecycle, robots
from scripts.pettripfinder.discovery import terms_registry as TR
from scripts.pettripfinder.discovery import url_record as U
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.run_context import DiscoveryRunContext

EFFECTIVE = "2026-08-03"


def _record(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
                canonical_category=C.CATEGORY_HOTEL, name="Test Hotel",
                normalized_name="test hotel", address_line="1 Main St",
                city="Columbus", state="OH", postal_code="43215",
                observed_at=EFFECTIVE, eligibility_state=C.ELIGIBILITY_ELIGIBLE)
    base.update(kw)
    return DiscoveryRecord(**base)


def _candidate(**kw):
    records = kw.pop("records", None) or (_record(),)
    base = dict(candidate_id="dc_test0001", source_records=records,
                name=records[0].name, normalized_name=records[0].normalized_name,
                address_line=records[0].address_line, city=records[0].city,
                state=records[0].state, postal_code=records[0].postal_code,
                provider_ids=tuple((r.provider, r.provider_record_id) for r in records))
    base.update(kw)
    return DiscoveryCandidate(**base)


def _context():
    return DiscoveryRunContext(run_id="run-001", effective_time=EFFECTIVE)


# =========================================================================== #
# Step 6 -- idempotency + FD-2 requeue guard.
# =========================================================================== #

class TestFD2RequeueGuard:
    def test_the_taxonomy_is_exactly_the_approved_eleven(self):
        assert idempotency.REVERIFICATION_REASONS == {
            "POLICY_STALE", "OFFICIAL_URL_CHANGED", "PROPERTY_IDENTITY_CHANGED",
            "PROPERTY_REBRANDED", "PROPERTY_RENAMED", "PROPERTY_LIFECYCLE_CHANGED",
            "SOURCE_CONTRADICTION", "HUMAN_CORRECTION", "CONTRACT_VERSION_CHANGED",
            "SCHEDULED_REVERIFICATION", "PROVIDER_RECORD_CHANGED",
        }

    @pytest.mark.parametrize("state", ["VERIFIED", "PUBLISHED", "HELD", "QUEUED"])
    def test_a_protected_hotel_needs_a_reason(self, state):
        with pytest.raises(idempotency.RequeueBlocked):
            idempotency.assert_requeue_allowed(state)

    @pytest.mark.parametrize("state", ["VERIFIED", "PUBLISHED", "HELD", "QUEUED"])
    def test_a_protected_hotel_with_a_valid_reason_may_requeue(self, state):
        idempotency.assert_requeue_allowed(state, reason=idempotency.POLICY_STALE)

    def test_free_text_cannot_replace_the_enum(self):
        """FD-2: explanation may SUPPLEMENT, never substitute."""
        with pytest.raises(idempotency.RequeueBlocked) as exc:
            idempotency.assert_requeue_allowed(
                "PUBLISHED", explanation="the operator said it looked wrong")
        assert "not a substitute" in str(exc.value)

    def test_free_text_may_supplement_a_real_reason(self):
        idempotency.assert_requeue_allowed(
            "PUBLISHED", reason=idempotency.HUMAN_CORRECTION,
            explanation="operator spotted a stale fee")

    def test_an_invented_reason_is_refused(self):
        with pytest.raises(idempotency.RequeueBlocked):
            idempotency.assert_requeue_allowed("VERIFIED", reason="SEEMS_OLD")

    def test_an_unprotected_hotel_needs_no_reason(self):
        idempotency.assert_requeue_allowed("NEW_CANDIDATE")

    def test_a_discovery_pet_signal_can_never_justify_requeue(self):
        """The Membrane restated at the requeue boundary (FD-2)."""
        for signal in ("pet_friendly", "allows_dogs", "directory_tag"):
            with pytest.raises(idempotency.RequeueBlocked):
                idempotency.assert_reason_not_from_discovery_signal(signal)


class TestSingleActiveRules:
    def test_the_queue_key_is_candidate_plus_contract_version(self):
        assert idempotency.queue_entry_key("dc_a", "1.1.0") == ("dc_a", "1.1.0")

    def test_a_rerun_under_the_same_contract_does_not_duplicate(self):
        existing = {("dc_a", "1.1.0"): "qe_same"}
        plan = idempotency.plan_activation(existing, [("dc_a", "1.1.0", "qe_same")])
        assert plan.unchanged_entries == ("qe_same",)
        assert plan.new_entries == () and plan.superseded_entries == ()

    def test_a_contract_bump_creates_a_new_active_entry(self):
        """Not a silent overwrite: work verified under 1.0.0 stays addressable."""
        existing = {("dc_a", "1.0.0"): "qe_old"}
        plan = idempotency.plan_activation(existing, [("dc_a", "1.1.0", "qe_new")])
        assert plan.new_entries == ("qe_new",)
        assert plan.superseded_entries == ()

    def test_a_changed_entry_under_the_same_key_supersedes(self):
        existing = {("dc_a", "1.1.0"): "qe_old"}
        plan = idempotency.plan_activation(existing, [("dc_a", "1.1.0", "qe_new")])
        assert plan.superseded_entries == (("qe_old", "qe_new"),)

    def test_duplicate_provider_records_are_refused(self):
        r = _record()
        with pytest.raises(idempotency.IdempotencyError):
            idempotency.assert_single_active_provider_records([r, r])

    def test_a_superseded_candidate_is_not_an_active_duplicate(self):
        live = _candidate()
        old = _candidate(superseded_by="dc_test0001")
        idempotency.assert_single_active_candidates([live, old])


# =========================================================================== #
# Step 7 -- supersession + merge history.
# =========================================================================== #

class TestHistory:
    def test_a_supersession_requires_a_known_reason(self):
        with pytest.raises(history.HistoryError):
            history.supersede("a", "b", reason="BECAUSE", context=_context())

    def test_an_entry_cannot_supersede_itself(self):
        with pytest.raises(history.HistoryError):
            history.supersede("a", "a", reason=history.SUPERSEDED_BY_RERUN,
                              context=_context())

    def test_a_valid_supersession_is_bound_to_the_run(self):
        rec = history.supersede("a", "b", reason=history.SUPERSEDED_BY_RERUN,
                                context=_context())
        assert rec.run_id == "run-001" and rec.effective_time == EFFECTIVE

    def test_a_note_supplements_but_the_reason_is_still_required(self):
        rec = history.supersede("a", "b", reason=history.SUPERSEDED_BY_OPERATOR,
                                context=_context(), note="operator merged twins")
        assert rec.reason and rec.note

    def test_merge_evidence_is_copied_from_dedup_not_recomputed(self):
        """deduplicate already recorded WHY; history stores that verbatim."""
        a = _record(provider_record_id="gp1")
        b = _record(provider=C.PROVIDER_OPENSTREETMAP, provider_record_id="osm1")
        cand = _candidate(records=(a, b),
                          merge_reason="phone_plus_compatible_name,same_normalized_address")
        rec = history.merge_record_for(cand, run_id="run-001")
        assert rec.component_evidence == ("phone_plus_compatible_name",
                                          "same_normalized_address")
        assert set(rec.merged_candidate_ids) == {"GOOGLE_PLACES:gp1", "OPENSTREETMAP:osm1"}

    def test_a_single_source_candidate_has_no_merge_record(self):
        assert history.merge_record_for(_candidate()) is None

    def test_a_merge_with_no_evidence_is_refused(self):
        with pytest.raises(history.HistoryError):
            history.MergeHistoryRecord(
                surviving_candidate_id="dc_a", merged_candidate_ids=("x",),
                component_evidence=()).validate()


# =========================================================================== #
# Step 8 -- lifecycle (FD-4).
# =========================================================================== #

class TestLifecycle:
    def test_the_review_owner_is_recorded(self):
        assert "Jonathan Fields" in lifecycle.REVIEW_OWNER

    def test_the_destructive_set_is_exactly_fd4s(self):
        assert lifecycle.DESTRUCTIVE_STATES == {
            "PERMANENTLY_CLOSED", "DEMOLISHED_OR_NO_LONGER_HOTEL",
            "CONVERTED_TO_NEW_BRAND"}

    @pytest.mark.parametrize("state", sorted(lifecycle.DESTRUCTIVE_STATES))
    def test_a_destructive_change_to_a_published_property_needs_approval(self, state):
        assert lifecycle.disposition_for(state, is_published=True) == \
            lifecycle.DISPOSITION_REQUIRES_HUMAN_APPROVAL

    def test_an_identity_changing_rebrand_is_destructive(self):
        assert lifecycle.is_destructive(lifecycle.REBRANDED, identity_changing=True)
        assert lifecycle.disposition_for(lifecycle.REBRANDED, is_published=True,
                                         identity_changing=True) == \
            lifecycle.DISPOSITION_REQUIRES_HUMAN_APPROVAL

    def test_a_name_change_alone_is_not_destructive(self):
        """Amendment §A6: a name/brand change alone never creates or destroys
        a hotel."""
        assert not lifecycle.is_destructive(lifecycle.RENAMED)

    def test_a_non_destructive_change_to_a_published_property_is_still_not_silent(self):
        assert lifecycle.disposition_for(lifecycle.ACTIVE, is_published=True) == \
            lifecycle.DISPOSITION_STAGED_FOR_REVIEW

    def test_closed_signal_maps_to_permanently_closed(self):
        cand = _candidate(records=(_record(
            eligibility_state=C.ELIGIBILITY_PERMANENTLY_CLOSED),))
        p = lifecycle.propose_lifecycle(cand, is_published=True)
        assert p.proposed_state == lifecycle.PERMANENTLY_CLOSED
        assert p.disposition == lifecycle.DISPOSITION_REQUIRES_HUMAN_APPROVAL
        assert p.review_owner == lifecycle.REVIEW_OWNER

    def test_possible_rebrand_proposes_rebranded_and_is_identity_changing(self):
        p = lifecycle.propose_lifecycle(_candidate(), is_published=True,
                                        identity_outcome=C.IDENTITY_POSSIBLE_REBRAND)
        assert p.proposed_state == lifecycle.REBRANDED and p.identity_changing

    def test_a_proposal_always_states_its_evidence(self):
        p = lifecycle.propose_lifecycle(_candidate())
        assert p.evidence

    def test_a_proposal_needing_approval_cannot_be_applied_by_code(self):
        p = lifecycle.propose_lifecycle(
            _candidate(records=(_record(eligibility_state=C.ELIGIBILITY_PERMANENTLY_CLOSED),)),
            is_published=True)
        with pytest.raises(lifecycle.LifecycleError):
            lifecycle.assert_not_silently_applied(p)

    def test_a_rebrand_preserves_names_urls_and_historical_provider_ids(self):
        cand = _candidate(records=(_record(website_url="https://old.example.com"),),
                          website_url="https://old.example.com")
        pres = lifecycle.preserve_through_rebrand(
            cand, new_name="New Brand Hotel", redirect_evidence=("301 old -> new",))
        assert "Test Hotel" in pres.preserved_names
        assert "New Brand Hotel" in pres.preserved_names
        assert "https://old.example.com" in pres.preserved_urls
        assert "GOOGLE_PLACES:gp1" in pres.historical_provider_ids
        assert pres.redirect_evidence == ("301 old -> new",)


# =========================================================================== #
# Step 9 -- URL revalidation (FD-5).
# =========================================================================== #

class TestFD5Identity:
    def test_two_independent_stable_keys_establish_identity(self):
        check, why = U.same_property_identity(U.IdentityKeyAgreement(
            agreeing_keys=(U.KEY_NORMALIZED_STREET_ADDRESS, U.KEY_PROPERTY_PHONE)))
        assert check == U.IDENTITY_PASS and "2 independent" in why

    def test_one_key_is_not_enough(self):
        check, _ = U.same_property_identity(U.IdentityKeyAgreement(
            agreeing_keys=(U.KEY_PROPERTY_PHONE,)))
        assert check == U.IDENTITY_FAIL

    def test_name_alone_never_establishes_identity(self):
        check, why = U.same_property_identity(U.IdentityKeyAgreement(
            non_identity_signals_seen=("name", "page_title")))
        assert check == U.IDENTITY_FAIL and "name alone never" in why

    def test_a_conflicting_stable_key_fails_outright(self):
        """A disagreeing stable key is evidence of a different property, not
        noise to be outvoted by two agreeing ones."""
        check, _ = U.same_property_identity(U.IdentityKeyAgreement(
            agreeing_keys=(U.KEY_NORMALIZED_STREET_ADDRESS, U.KEY_PROPERTY_PHONE),
            conflicting_keys=(U.KEY_OFFICIAL_PROPERTY_ID,)))
        assert check == U.IDENTITY_FAIL

    def test_duplicate_keys_do_not_count_twice(self):
        check, _ = U.same_property_identity(U.IdentityKeyAgreement(
            agreeing_keys=(U.KEY_PROPERTY_PHONE, U.KEY_PROPERTY_PHONE)))
        assert check == U.IDENTITY_FAIL

    def test_an_unknown_key_is_refused(self):
        with pytest.raises(U.UrlRecordError):
            U.same_property_identity(U.IdentityKeyAgreement(agreeing_keys=("vibes",)))


class TestFD5Revalidation:
    def _record(self, **kw):
        base = dict(url="https://www.marriott.com/en-us/hotels/x/overview/",
                    status=C.WEBSITE_RES_PROPERTY_URL_CONFIRMED,
                    last_validated_at="2026-08-01",
                    property_identity_check=U.IDENTITY_PASS)
        base.update(kw)
        return U.OfficialUrlRecord(**base)

    def test_default_cadence_is_thirty_days(self):
        assert U.DEFAULT_REVALIDATION_CADENCE_DAYS == 30
        assert self._record().revalidation_cadence_days == 30

    def test_fresh_within_cadence(self):
        assert not U.is_stale(self._record(), as_of="2026-08-20")

    def test_stale_past_cadence(self):
        assert U.is_stale(self._record(), as_of="2026-09-15")

    def test_never_validated_is_stale(self):
        assert U.is_stale(self._record(last_validated_at=""), as_of="2026-08-02")

    @pytest.mark.parametrize("kwargs,expected", [
        ({"redirect_destination_changed": True}, U.TRIGGER_REDIRECT_CHANGED),
        ({"provider_record_changed": True}, U.TRIGGER_PROVIDER_RECORD_CHANGED),
        ({"rebrand_or_rename_proposed": True}, U.TRIGGER_REBRAND_OR_RENAME_PROPOSED),
        ({"identity_conflict": True}, U.TRIGGER_IDENTITY_CONFLICT),
    ])
    def test_each_immediate_trigger_fires(self, kwargs, expected):
        triggers = U.revalidation_triggers(self._record(), as_of="2026-08-02", **kwargs)
        assert expected in triggers

    def test_a_failed_identity_check_blocks_handoff(self):
        d = U.evaluate_handoff(
            self._record(property_identity_check=U.IDENTITY_FAIL,
                         identity_explanation="redirect resolves to a different property"),
            as_of="2026-08-02")
        assert not d.allowed and "FAIL" in d.reason

    def test_an_unchanged_property_passes(self):
        assert U.evaluate_handoff(self._record(), as_of="2026-08-02").allowed

    def test_a_redirect_with_an_unchecked_identity_blocks(self):
        d = U.evaluate_handoff(
            self._record(property_identity_check=U.IDENTITY_UNCHECKED,
                         canonical_destination="https://www.marriott.com/other/"),
            as_of="2026-08-02")
        assert not d.allowed and "never checked" in d.reason

    def test_a_stale_record_blocks_until_revalidated(self):
        d = U.evaluate_handoff(self._record(), as_of="2026-10-01")
        assert not d.allowed and U.TRIGGER_STALE in d.triggers


# =========================================================================== #
# Step 10 -- provider terms registry (FD-1).
# =========================================================================== #

class TestTermsRegistry:
    def _registry(self):
        return TR.load_registry()

    def test_the_committed_registry_loads(self):
        reg = self._registry()
        assert "GOOGLE_PLACES" in reg.provider_names()
        assert "OPENSTREETMAP" in reg.provider_names()

    def test_every_live_provider_starts_unreviewed(self):
        """FD-1. Entries were transcribed from code comments, not verified."""
        reg = self._registry()
        for name in ("GOOGLE_PLACES", "OPENSTREETMAP", "FOURSQUARE"):
            assert reg.get(name).review_state == TR.UNREVIEWED

    def test_no_live_provider_may_run(self):
        reg = self._registry()
        for name in ("GOOGLE_PLACES", "OPENSTREETMAP", "FOURSQUARE"):
            with pytest.raises(TR.TermsRegistryError):
                TR.assert_live_use_permitted(name, registry=reg, as_of=EFFECTIVE)

    def test_provider_zero_remains_eligible(self):
        """Not an exception: it has no third-party terms surface because it
        makes no third-party request."""
        TR.assert_live_use_permitted(TR.PROVIDER_ZERO, registry=self._registry(),
                                     as_of=EFFECTIVE)

    def test_a_provider_with_no_entry_cannot_be_instantiated(self):
        with pytest.raises(TR.TermsRegistryError):
            TR.assert_live_use_permitted("YELP", registry=self._registry(),
                                         as_of=EFFECTIVE)

    def test_a_reviewed_but_stale_entry_is_disabled(self):
        entry = TR.ProviderTermsEntry(
            provider_name="X", review_state=TR.REVIEWED,
            last_terms_review_date="2025-01-01", review_freshness_days=180,
            enabled=True)
        reg = TR.ProviderTermsRegistry(registry_version="t", entries=(entry,))
        with pytest.raises(TR.TermsRegistryError):
            TR.assert_live_use_permitted("X", registry=reg, as_of=EFFECTIVE)

    def test_reviewed_claims_require_a_date(self):
        with pytest.raises(TR.TermsRegistryError):
            TR.ProviderTermsEntry(provider_name="X", review_state=TR.REVIEWED).validate()

    def test_osm_attribution_is_recorded(self):
        assert "OpenStreetMap" in TR.attribution_for("OPENSTREETMAP",
                                                     registry=self._registry())


# =========================================================================== #
# Step 11 -- robots.txt, fail-closed (FD-6).
# =========================================================================== #

def _fetch(text, ok=True, status=200):
    return lambda url: robots.RobotsFetchResult(
        ok=ok, text=text, http_status=status, retrieved_at=EFFECTIVE)


class TestRobotsFailClosed:
    def test_disallow_blocks(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/private/x", cache=cache,
                             robots_fetcher=_fetch("User-agent: *\nDisallow: /private"))
        assert d.decision == robots.DENIED
        assert d.matched_rule == "Disallow: /private"

    def test_allow_permits(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/public/x", cache=cache,
                             robots_fetcher=_fetch("User-agent: *\nDisallow: /private"))
        assert d.decision == robots.ALLOWED

    def test_unreachable_robots_denies_the_host(self):
        """Base §C.2 fail-closed rule."""
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/x", cache=cache,
                             robots_fetcher=lambda u: robots.RobotsFetchResult(ok=False))
        assert d.decision == robots.DENIED
        assert d.reason == robots.REASON_UNREACHABLE

    def test_malformed_robots_is_indeterminate_and_blocks(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/x", cache=cache,
                             robots_fetcher=_fetch("<html>not robots at all</html>"))
        assert d.decision == robots.INDETERMINATE
        assert d.decision in robots.BLOCKING_DECISIONS

    def test_empty_robots_permits(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/x", cache=cache, robots_fetcher=_fetch(""))
        assert d.decision == robots.ALLOWED
        assert d.reason == robots.REASON_EMPTY_ROBOTS

    def test_a_specific_agent_group_beats_the_wildcard(self):
        cache = robots.RobotsCache()
        text = ("User-agent: *\nDisallow: /\n\n"
                "User-agent: AtlasDiscovery\nDisallow: /admin\n")
        d = robots.check_url("https://h.test/rooms", cache=cache,
                             robots_fetcher=_fetch(text),
                             user_agent="AtlasDiscovery")
        assert d.decision == robots.ALLOWED

    def test_the_specific_group_still_blocks_its_own_disallow(self):
        cache = robots.RobotsCache()
        text = ("User-agent: *\nDisallow:\n\n"
                "User-agent: AtlasDiscovery\nDisallow: /admin\n")
        d = robots.check_url("https://h.test/admin/x", cache=cache,
                             robots_fetcher=_fetch(text), user_agent="AtlasDiscovery")
        assert d.decision == robots.DENIED

    def test_a_longer_allow_beats_a_shorter_disallow(self):
        cache = robots.RobotsCache()
        text = "User-agent: *\nDisallow: /hotels\nAllow: /hotels/columbus\n"
        d = robots.check_url("https://h.test/hotels/columbus/x", cache=cache,
                             robots_fetcher=_fetch(text))
        assert d.decision == robots.ALLOWED

    def test_the_decision_is_cached_per_host(self):
        calls = []

        def counting(url):
            calls.append(url)
            return robots.RobotsFetchResult(ok=True, text="User-agent: *\nDisallow:",
                                            http_status=200, retrieved_at=EFFECTIVE)

        cache = robots.RobotsCache()
        robots.check_url("https://h.test/a", cache=cache, robots_fetcher=counting)
        robots.check_url("https://h.test/b", cache=cache, robots_fetcher=counting)
        assert len(calls) == 1
        assert cache.hosts() == ("h.test",)

    def test_retrieval_metadata_is_kept_with_the_decision(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/x", cache=cache,
                             robots_fetcher=_fetch("User-agent: *\nDisallow:"))
        assert d.retrieved_at == EFFECTIVE and d.http_status == 200
        assert d.source_url == "https://h.test/robots.txt"

    def test_assert_raises_on_a_blocking_decision(self):
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/private", cache=cache,
                             robots_fetcher=_fetch("User-agent: *\nDisallow: /private"))
        with pytest.raises(robots.RobotsError):
            robots.assert_retrieval_permitted(d)


class TestRobotsProviderZeroPosture:
    def test_the_default_makes_no_network_request_and_blocks(self):
        """Provider Zero requirement: cache-only, zero network calls. With no
        fetcher injected there is no code path to the network, and an uncached
        host is INDETERMINATE -- which blocks rather than silently permits."""
        cache = robots.RobotsCache()
        d = robots.check_url("https://h.test/x", cache=cache)      # no fetcher
        assert d.decision == robots.INDETERMINATE
        assert d.reason == robots.REASON_NOT_FETCHED
        assert d.decision in robots.BLOCKING_DECISIONS

    def test_a_cached_host_still_decides_without_any_fetch(self):
        cache = robots.RobotsCache()
        cache.put("h.test", robots.RobotsFetchResult(
            ok=True, text="User-agent: *\nDisallow: /private",
            http_status=200, retrieved_at=EFFECTIVE))
        allowed = robots.check_url("https://h.test/rooms", cache=cache)
        denied = robots.check_url("https://h.test/private/x", cache=cache)
        assert allowed.decision == robots.ALLOWED
        assert denied.decision == robots.DENIED

    def test_no_bypass_or_alternate_identity_path_exists(self):
        """FD-6: no stealth, bypass, alternate identity or proxy workaround.
        Structural check -- the module must not contain retry-under-another-
        name machinery."""
        src = (pathlib.Path(robots.__file__)).read_text(encoding="utf-8")
        tree = __import__("ast").parse(src)
        names = {n.name for n in __import__("ast").walk(tree)
                 if isinstance(n, __import__("ast").FunctionDef)}
        for forbidden in ("rotate_user_agent", "retry_with_agent", "bypass",
                          "use_proxy", "spoof"):
            assert forbidden not in names
