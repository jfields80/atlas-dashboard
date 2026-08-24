"""PTF-MEASUREMENT-001 Phase 1b -- affiliate destinations as authority.

Every refusal is a raise. The one thing that is NOT a refusal -- no mapping
for a property -- is ``None``, and ``None`` is today's booking behaviour.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import affiliate_destinations as AD
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.commercial_actions import ACTION_BOOKING
from scripts.pettripfinder.site_enrichment import build_go_pages_for_listing

SEED_ROW = {"name": "Aloft Columbus Easton", "market_id": "columbus-oh",
            "website_url": "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/",
            "phone": "614-555-0100", "address": "1 A St", "city": "Columbus", "state": "OH"}

PROVIDER = {"provider_id": "acme-network", "display_name": "Acme Hotel Network",
            "allowed_destination_hosts": ["go.acme.test"],
            "disclosure": "PetTripFinder may earn a commission.",
            "rel": AD.REL_AFFILIATE, "enrolled": True}

ROW = {"identity_key": "aloft columbus easton", "provider_id": "acme-network",
       "program_id": "marriott-us", "destination_url": "https://go.acme.test/c/123?u=cmhea",
       "official_url_at_mapping": SEED_ROW["website_url"], "approved_by": "A Human",
       "approved_at": "2026-08-22", "status": "active"}


def _providers(**over):
    p = dict(PROVIDER, **over)
    return AD.providers_from_document({"schema": AD.PROVIDERS_SCHEMA, "count": 1,
                                       "providers": [p]})


def _shard(rows, market_id="columbus-oh"):
    doc = AD.empty_document(market_id)
    doc["destinations"] = list(rows)
    doc["count"] = len(rows)
    return doc


# --------------------------------------------------------------------------- #
# Committed state
# --------------------------------------------------------------------------- #

class TestCommittedState:
    def test_the_registry_is_empty_and_valid(self):
        doc = json.loads(AD.PROVIDERS_PATH.read_text(encoding="utf-8"))
        assert doc["schema"] == AD.PROVIDERS_SCHEMA
        assert AD.validate_providers_document(doc) == []
        assert AD.load_providers() == {}

    def test_every_registered_market_has_an_empty_shard(self):
        for market_id in MA.sharded_market_ids():
            path = MA.affiliate_shard_path(market_id)
            assert path.is_file(), market_id
            doc = AD.load_market_destinations_document(market_id)
            assert doc["count"] == 0 and doc["destinations"] == []
            assert doc["market_id"] == market_id

    def test_the_global_view_is_empty(self):
        assert AD.assemble_global_view() == {}

    def test_the_shard_kind_is_registered_additively(self):
        assert MA.AFFILIATE_SHARD_NAME == "affiliate_destinations.json"
        assert "AFFILIATE_SHARD_NAME" in MA.__all__ and "affiliate_shard_path" in MA.__all__
        # The three legacy globals and their manifest know nothing of it.
        assert not any("affiliate" in str(p) for p, _ in MA.generated_artifacts())

    def test_the_committed_shards_are_what_empty_document_renders(self):
        for market_id in MA.sharded_market_ids():
            expected = MA.render_json(AD.empty_document(market_id)).encode("utf-8")
            assert MA.affiliate_shard_path(market_id).read_bytes() == expected, market_id

    def test_resolution_against_the_committed_shards_is_none_for_every_seed_hotel(self):
        for market_id in MA.sharded_market_ids():
            providers = AD.load_providers()
            shard = AD.load_market_destinations_document(market_id)
            for row in MA.load_market_seed_rows(market_id):
                assert AD.destination_for(row, market_id, providers=providers,
                                          destinations=shard) is None


# --------------------------------------------------------------------------- #
# Provider registry validation
# --------------------------------------------------------------------------- #

class TestProviders:
    def test_a_valid_provider_loads(self):
        assert _providers()["acme-network"].enrolled is True

    def test_rel_policy_is_fixed(self):
        with pytest.raises(AD.AffiliateDestinationError):
            _providers(rel="nofollow")

    def test_hosts_must_be_bare_lowercase_hostnames(self):
        with pytest.raises(AD.AffiliateDestinationError):
            _providers(allowed_destination_hosts=["https://go.acme.test"])
        with pytest.raises(AD.AffiliateDestinationError):
            _providers(allowed_destination_hosts=[])

    def test_duplicate_provider_ids_are_refused(self):
        doc = {"schema": AD.PROVIDERS_SCHEMA, "count": 2, "providers": [PROVIDER, PROVIDER]}
        assert any("duplicates" in p for p in AD.validate_providers_document(doc))

    def test_a_count_that_lies_is_refused(self):
        doc = {"schema": AD.PROVIDERS_SCHEMA, "count": 0, "providers": [PROVIDER]}
        assert AD.validate_providers_document(doc)

    def test_unknown_keys_are_refused(self):
        with pytest.raises(AD.AffiliateDestinationError):
            _providers(api_key="secret")


# --------------------------------------------------------------------------- #
# Shard validation
# --------------------------------------------------------------------------- #

class TestShardValidation:
    def test_a_valid_row_validates(self):
        assert AD.validate_destinations_document(_shard([ROW]), "columbus-oh") == []

    def test_market_mismatch_is_refused(self):
        assert any("market_id" in p for p in
                   AD.validate_destinations_document(_shard([ROW]), "dayton-oh"))

    def test_duplicate_identity_is_refused(self):
        assert any("duplicates" in p for p in
                   AD.validate_destinations_document(_shard([ROW, ROW]), "columbus-oh"))

    def test_identity_key_must_be_normalized(self):
        bad = dict(ROW, identity_key="Aloft Columbus Easton")
        assert any("normalized" in p for p in
                   AD.validate_destinations_document(_shard([bad]), "columbus-oh"))

    @pytest.mark.parametrize("url", [
        "http://go.acme.test/x", "go.acme.test/x", "https://user:pw@go.acme.test/x",
        'https://go.acme.test/x"onclick', "", "https://go.acme.test/x y",
    ])
    def test_malformed_destination_is_refused(self, url):
        bad = dict(ROW, destination_url=url)
        assert AD.validate_destinations_document(_shard([bad]), "columbus-oh")

    def test_approval_is_a_human_attestation(self):
        assert AD.validate_destinations_document(_shard([dict(ROW, approved_by="")]),
                                                 "columbus-oh")
        assert AD.validate_destinations_document(_shard([dict(ROW, approved_at="soon")]),
                                                 "columbus-oh")

    def test_status_is_an_enum(self):
        assert AD.validate_destinations_document(_shard([dict(ROW, status="live")]),
                                                 "columbus-oh")

    def test_a_missing_shard_is_an_empty_shard(self, tmp_path):
        doc = AD.load_market_destinations_document("columbus-oh", authority_dir=tmp_path)
        assert doc["count"] == 0

    def test_a_malformed_shard_raises(self, tmp_path):
        (tmp_path / "columbus-oh").mkdir()
        (tmp_path / "columbus-oh" / MA.AFFILIATE_SHARD_NAME).write_text("{", encoding="utf-8")
        with pytest.raises(AD.AffiliateDestinationError):
            AD.load_market_destinations_document("columbus-oh", authority_dir=tmp_path)

    def test_one_identity_mapped_by_two_markets_is_refused(self, tmp_path):
        for market_id in ("columbus-oh", "dayton-oh"):
            (tmp_path / market_id).mkdir()
            (tmp_path / market_id / MA.AFFILIATE_SHARD_NAME).write_text(
                json.dumps(_shard([ROW], market_id)), encoding="utf-8")
        with pytest.raises(AD.AffiliateDestinationError):
            AD.assemble_global_view(tmp_path, market_ids=("columbus-oh", "dayton-oh"))


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #

class TestResolution:
    def test_empty_registry_and_empty_shard_resolve_to_none(self):
        assert AD.destination_for(SEED_ROW, "columbus-oh", providers={},
                                  destinations=_shard([])) is None

    def test_missing_destination_falls_back_to_none(self):
        assert AD.destination_for(dict(SEED_ROW, name="Some Other Hotel"), "columbus-oh",
                                  providers=_providers(), destinations=_shard([ROW])) is None

    def test_a_real_destination_resolves(self):
        dest = AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(),
                                  destinations=_shard([ROW]))
        assert dest == AD.AffiliateDestination(provider_id="acme-network",
                                               destination_url=ROW["destination_url"],
                                               rel=AD.REL_AFFILIATE)

    def test_enrolled_false_refuses(self):
        with pytest.raises(AD.AffiliateDestinationError, match="not enrolled"):
            AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(enrolled=False),
                               destinations=_shard([ROW]))

    def test_unknown_provider_refuses(self):
        with pytest.raises(AD.AffiliateDestinationError, match="not in the registry"):
            AD.destination_for(SEED_ROW, "columbus-oh", providers={},
                               destinations=_shard([ROW]))

    def test_host_must_be_allowlisted(self):
        with pytest.raises(AD.AffiliateDestinationError, match="not allowlisted"):
            AD.destination_for(SEED_ROW, "columbus-oh",
                               providers=_providers(allowed_destination_hosts=["other.test"]),
                               destinations=_shard([ROW]))

    def test_a_subdomain_of_an_allowlisted_host_is_allowed_but_a_lookalike_is_not(self):
        ok = dict(ROW, destination_url="https://eu.go.acme.test/c/1")
        assert AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(),
                                  destinations=_shard([ok])) is not None
        bad = dict(ROW, destination_url="https://go.acme.test.evil.test/c/1")
        with pytest.raises(AD.AffiliateDestinationError):
            AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(),
                               destinations=_shard([bad]))

    def test_official_url_drift_refuses(self):
        moved = dict(SEED_ROW, website_url="https://www.marriott.com/somewhere-else/")
        with pytest.raises(AD.AffiliateDestinationError, match="drifted"):
            AD.destination_for(moved, "columbus-oh", providers=_providers(),
                               destinations=_shard([ROW]))

    def test_market_mismatch_refuses(self):
        foreign = dict(SEED_ROW, market_id="dayton-oh")
        with pytest.raises(AD.AffiliateDestinationError):
            AD.destination_for(foreign, "columbus-oh", providers=_providers(),
                               destinations=_shard([ROW]))

    def test_unknown_identity_in_shard_is_unbound_at_the_gate(self, tmp_path):
        """A shard row for a property the market does not seed cannot be
        resolved by any seed row (destination_for never sees it) and the
        identity gate names it."""
        (tmp_path / "columbus-oh").mkdir()
        ghost = dict(ROW, identity_key="hotel that does not exist")
        (tmp_path / "columbus-oh" / MA.AFFILIATE_SHARD_NAME).write_text(
            json.dumps(_shard([ghost])), encoding="utf-8")
        for name in (MA.ROUTING_SHARD_NAME, MA.EXCLUSIONS_SHARD_NAME, MA.SEED_SHARD_NAME):
            src = MA.market_shard_dir("columbus-oh") / name
            (tmp_path / "columbus-oh" / name).write_bytes(src.read_bytes())
        reg = tmp_path / "providers.json"
        reg.write_text(json.dumps({"schema": AD.PROVIDERS_SCHEMA, "count": 1,
                                   "providers": [PROVIDER]}), encoding="utf-8")
        gates = {}
        AD.run_affiliate_gates(gates, _gate, authority_dir=tmp_path, providers_path=reg,
                               market_ids=("columbus-oh",))
        assert not gates[AD.GATE_IDENTITY_BOUND]["pass"]
        assert gates[AD.GATE_ALLOWLISTED]["pass"] and gates[AD.GATE_ENROLLED]["pass"]

    def test_duplicate_destination_rows_refuse(self):
        doc = _shard([ROW, ROW])
        with pytest.raises(AD.AffiliateDestinationError, match="2 destination rows"):
            AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(),
                               destinations=doc)

    def test_suspended_status_refuses(self):
        with pytest.raises(AD.AffiliateDestinationError, match="status"):
            AD.destination_for(SEED_ROW, "columbus-oh", providers=_providers(),
                               destinations=_shard([dict(ROW, status="suspended")]))


# --------------------------------------------------------------------------- #
# Booking plumbing
# --------------------------------------------------------------------------- #

class TestBookingPlumbing:
    def _pages(self, dest):
        return build_go_pages_for_listing(
            listing_id="aloft-columbus-easton", name=SEED_ROW["name"],
            official_url=SEED_ROW["website_url"], phone=SEED_ROW["phone"],
            address=SEED_ROW["address"], city=SEED_ROW["city"], state=SEED_ROW["state"],
            category_slug="pet-friendly-hotels", corridor="", include_booking=True,
            verification_status="VERIFIED_PET_FRIENDLY", affiliate_destination=dest)

    def test_fallback_booking_page_is_the_official_url_with_no_provider(self):
        plain = self._pages(None)
        booking = plain["/go/aloft-columbus-easton/booking/index.html"]
        assert SEED_ROW["website_url"] in booking
        assert '"affiliate_provider": ""' in booking
        assert 'rel="noopener"' in booking
        assert plain == self._pages(dest=None)

    def test_fallback_is_identical_to_not_passing_the_argument(self):
        plain = self._pages(None)
        legacy = build_go_pages_for_listing(
            listing_id="aloft-columbus-easton", name=SEED_ROW["name"],
            official_url=SEED_ROW["website_url"], phone=SEED_ROW["phone"],
            address=SEED_ROW["address"], city=SEED_ROW["city"], state=SEED_ROW["state"],
            category_slug="pet-friendly-hotels", corridor="", include_booking=True,
            verification_status="VERIFIED_PET_FRIENDLY")
        assert plain == legacy

    def test_a_real_destination_populates_the_booking_page_only(self):
        dest = AD.AffiliateDestination(provider_id="acme-network",
                                       destination_url=ROW["destination_url"])
        pages = self._pages(dest)
        booking = pages["/go/aloft-columbus-easton/booking/index.html"]
        assert ROW["destination_url"] in booking
        assert '"affiliate_provider": "acme-network"' in booking
        assert 'rel="nofollow sponsored noopener"' in booking
        official = pages["/go/aloft-columbus-easton/official-website/index.html"]
        assert SEED_ROW["website_url"] in official
        assert '"affiliate_provider": ""' in official
        assert 'rel="noopener"' in official
        assert ROW["destination_url"] not in official

    def test_redirect_target_prefers_an_explicit_booking_destination(self):
        from scripts.pettripfinder.commercial_actions import build_redirect_target
        assert build_redirect_target(ACTION_BOOKING, official_url="https://x.test/",
                                     phone="", booking_destination="https://aff.test/1") \
            == "https://aff.test/1"
        assert build_redirect_target(ACTION_BOOKING, official_url="https://x.test/",
                                     phone="") == "https://x.test/"


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #

def _gate(gates, gate_id, passed, detail=""):
    gates[gate_id] = {"pass": bool(passed), "detail": detail}


class TestGates:
    def test_all_three_pass_on_the_committed_empty_state(self):
        gates = {}
        assert AD.run_affiliate_gates(gates, _gate) == 0
        assert [g for g in AD.AFFILIATE_GATES if not gates[g]["pass"]] == []

    def test_an_unreadable_registry_fails_all_three(self, tmp_path):
        gates = {}
        AD.run_affiliate_gates(gates, _gate, providers_path=tmp_path / "none.json")
        assert all(not gates[g]["pass"] for g in AD.AFFILIATE_GATES)

    def test_an_unenrolled_mapping_fails_the_enrolled_gate(self, tmp_path):
        (tmp_path / "columbus-oh").mkdir()
        for name in (MA.ROUTING_SHARD_NAME, MA.EXCLUSIONS_SHARD_NAME, MA.SEED_SHARD_NAME):
            src = MA.market_shard_dir("columbus-oh") / name
            (tmp_path / "columbus-oh" / name).write_bytes(src.read_bytes())
        (tmp_path / "columbus-oh" / MA.AFFILIATE_SHARD_NAME).write_text(
            json.dumps(_shard([ROW])), encoding="utf-8")
        reg = tmp_path / "providers.json"
        reg.write_text(json.dumps({"schema": AD.PROVIDERS_SCHEMA, "count": 1,
                                   "providers": [dict(PROVIDER, enrolled=False)]}),
                       encoding="utf-8")
        gates = {}
        AD.run_affiliate_gates(gates, _gate, authority_dir=tmp_path, providers_path=reg,
                               market_ids=("columbus-oh",))
        assert not gates[AD.GATE_ENROLLED]["pass"]
        assert gates[AD.GATE_IDENTITY_BOUND]["pass"]
