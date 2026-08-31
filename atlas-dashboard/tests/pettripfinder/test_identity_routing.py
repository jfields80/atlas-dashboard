"""PTF-IDENTITY-ROUTING-P0-001 -- ptf-identity-routing/1.0 and its integration.

The load-bearing claim these tests defend is a NEGATIVE one: a routing record
says where a property speaks for itself, and cannot become publication. Most of
the file is therefore about what does NOT happen.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import identity_routing as IR
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.build_capture_queue import build_queue
from scripts.pettripfinder.site_data import normalize_name

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"


def record(**overrides):
    base = {
        "routing_id": "route-columbus-oh-sample-inn",
        "schema_version": IR.CONTRACT_VERSION,
        "hotel_ref": {"market_id": "columbus-oh",
                      "canonical_name": "Sample Inn Columbus",
                      "normalized_name": "sample inn columbus"},
        "market_id": "columbus-oh",
        "official_property_url": "https://www.marriott.com/en-us/hotels/xxxxx-sample/overview/",
        "official_domain": "marriott.com",
        "property_code": "XXXXX",
        "brand": "MARRIOTT",
        "binding_method": IR.BINDING_BRAND_INDEX,
        "binding_sources": ["chamber directory anchor"],
        "identity_signals_matched": ["street", "zip"],
        "observed_at": "2026-08-08",
        "verified_at": "2026-08-08",
        "status": IR.ROUTING_CONFIRMED,
    }
    base.update(overrides)
    return base


def authority(*records):
    return {"schema": IR.SCHEMA, "routes": list(records)}


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

def test_valid_record_round_trips():
    assert IR.validate_record(record())["routing_id"].startswith("route-")


def test_strict_keys_reject_unknown_field():
    with pytest.raises(IR.IdentityRoutingError, match="additionalProperties"):
        IR.validate_record(record(surprise="nope"))


def test_missing_required_field_fails():
    doc = record()
    del doc["binding_sources"]
    with pytest.raises(IR.IdentityRoutingError, match="missing required"):
        IR.validate_record(doc)


def test_policy_fields_are_forbidden():
    with pytest.raises(IR.IdentityRoutingError, match="pet-policy field"):
        IR.validate_record(record(pet_fee=5000))


def test_policy_fields_forbidden_inside_identity_context():
    with pytest.raises(IR.IdentityRoutingError, match="pet-policy field"):
        IR.validate_record(record(identity_context={"pets_allowed": "true"}))


def test_unknown_status_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="status"):
        IR.validate_record(record(status="PROBABLY_FINE"))


def test_binding_method_is_closed_and_never_upgraded():
    with pytest.raises(IR.IdentityRoutingError, match="rendered page"):
        IR.validate_record(record(binding_method="LOOKS_RIGHT"))
    assert IR.validate_record(
        record(binding_method=IR.BINDING_BRAND_INDEX))["binding_method"] \
        == IR.BINDING_BRAND_INDEX


def test_normalized_name_must_be_derivable_not_typed():
    with pytest.raises(IR.IdentityRoutingError, match="derivable"):
        IR.validate_record(record(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
            "normalized_name": "whatever i felt like"}))


def test_hotel_ref_may_not_carry_a_second_identifier():
    with pytest.raises(IR.IdentityRoutingError, match="never extends it"):
        IR.validate_record(record(hotel_ref={
            "market_id": "columbus-oh", "canonical_name": "Sample Inn Columbus",
            "normalized_name": "sample inn columbus",
            "atlas_hotel_id": "HOTEL-0001"}))


def test_market_id_must_match_identity_market():
    with pytest.raises(IR.IdentityRoutingError, match="does not match hotel_ref"):
        IR.validate_record(record(market_id="cleveland-akron-canton-oh"))


def test_third_party_domain_rejected_as_official():
    with pytest.raises(IR.IdentityRoutingError, match="never BE one"):
        IR.validate_record(record(
            official_property_url="https://www.booking.com/hotel/us/sample.html",
            official_domain="booking.com"))


def test_known_dead_parking_domain_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="never BE one"):
        IR.validate_record(record(
            official_property_url="https://www.comfortsuitesgrovecity.com/",
            official_domain="comfortsuitesgrovecity.com"))


def test_declared_domain_must_match_the_url():
    with pytest.raises(IR.IdentityRoutingError, match="does not match"):
        IR.validate_record(record(official_domain="hilton.com"))


def test_non_https_rejected():
    with pytest.raises(IR.IdentityRoutingError, match="https"):
        IR.validate_record(record(
            official_property_url="http://www.marriott.com/en-us/hotels/x/overview/"))


def test_confirmed_record_must_record_identity_signals():
    with pytest.raises(IR.IdentityRoutingError, match="identity signals"):
        IR.validate_record(record(identity_signals_matched=[]))


def test_binding_sources_must_be_present():
    with pytest.raises(IR.IdentityRoutingError, match="binding_sources"):
        IR.validate_record(record(binding_sources=[]))


# --------------------------------------------------------------------------- #
# Collisions
# --------------------------------------------------------------------------- #

def test_one_active_routing_record_per_identity():
    a = record(routing_id="route-a")
    b = record(routing_id="route-b")
    with pytest.raises(IR.IdentityRoutingError, match="two active routing records"):
        IR.validate_authority(authority(a, b))


def test_a_held_duplicate_is_allowed_beside_one_active():
    a = record(routing_id="route-a")
    b = record(routing_id="route-b", status=IR.ROUTING_HELD)
    assert len(IR.validate_authority(authority(a, b))) == 2


def test_duplicate_property_code_across_identities_rejected():
    a = record()
    b = record(routing_id="route-b",
               hotel_ref={"market_id": "columbus-oh", "canonical_name": "Other Inn",
                          "normalized_name": "other inn"},
               official_property_url="https://www.marriott.com/en-us/hotels/yyyyy-other/overview/")
    with pytest.raises(IR.IdentityRoutingError, match="property code"):
        IR.validate_authority(authority(a, b))


def test_duplicate_url_across_identities_rejected():
    a = record()
    b = record(routing_id="route-b", property_code="YYYYY",
               hotel_ref={"market_id": "columbus-oh", "canonical_name": "Other Inn",
                          "normalized_name": "other inn"})
    with pytest.raises(IR.IdentityRoutingError, match="URL .* binds two"):
        IR.validate_authority(authority(a, b))


# --------------------------------------------------------------------------- #
# The committed Columbus authority
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def routes():
    return IR.load_routes()


def test_committed_authority_validates(routes):
    # PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001: 20 Columbus + 60 Cleveland.
    # Routing is the mechanism for a CONFIRMED hotel that is NOT inventory, so
    # publishing 19 Cleveland hotels and excluding 8 retired their 27 routes --
    # 107 -> 80. A surviving route for a seeded hotel would be a second,
    # competing authority for the same identity.
    #
    # PTF-CLEVELAND-URL-RECOVERY-WORKER-002: 80 -> 167. 87 of the 102 hotels
    # classified NO_OFFICIAL_URL in cleveland_unresolved_manifest.json were
    # identity-verified (address and/or phone matched against the brand's own
    # domain, or an independent first-party site) and routed; Columbus is
    # unchanged at 20.
    # 167 -> 165: PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 retired the two Drury routes whose hotels became Cleveland inventory.
    #
    # 165 -> 174: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 is the first work to
    # route Dayton at all. Fourteen first-time bindings were proposed by the
    # ChatGPT Work browser pass for census rows that carry no _official_url;
    # nine were written (one CONFIRMED on a first-party fetch, eight HELD), four
    # were rejected, and the fourteenth -- Extended Stay America Select Suites
    # Dayton - Miamisburg -- is deliberately absent because that identity became
    # seed inventory in the same work order. See
    # test_no_committed_route_is_already_seed_inventory below, which is the rule
    # that absence obeys.
    # 87 after Pass 3; 90 after PTF-CLEVELAND-ROUTING-REPAIR-001 created routes for
    # the three official URLs it found (Magnuson Canton, Quality Inn
    # Akron South, the American Croatian Lodge).
    # 90 -> 300: PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C opened Cincinnati
    # routing for the first time, all 210 CONFIRMED (223 targets adjudicated,
    # 12 ROUTING_UNRESOLVED and 1 PROPERTY_CLOSED_OR_CONVERTED-with-no-URL
    # excluded). Columbus and Dayton are unchanged.
    # 300 -> 277: PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 retired 23
    # Cleveland routing placeholders as their identities each reached a
    # final publication or exclusion disposition (18 publications, incl. two
    # renames, and 5 verified-no-pets); a published or excluded identity no
    # longer needs a routing-only record.
    #
    # PTF-MARKET-AUTHORITY-SHARDING-001 stopped pinning the number. The routing
    # authority is now assembled from one shard per market, so the total is an
    # arithmetic consequence of seven independent files -- and pinning a
    # consequence meant every market's branch had to edit this line, which is
    # the shared-file contention sharding exists to remove. What is actually
    # under test is that the global authority is the union of the shards and
    # nothing else: no record invented in assembly, none dropped. The per-market
    # counts, which ARE exact truths owned by one market each, stay pinned in
    # test_routing_carries_more_than_one_market below.
    assert len(routes) == sum(len(MA.load_market_routes(m))
                              for m in MA.sharded_market_ids())


def test_committed_authority_split(routes):
    confirmed = [r for r in routes if r["status"] == IR.ROUTING_CONFIRMED]
    held = [r for r in routes if r["status"] == IR.ROUTING_HELD]
    retired = [r for r in routes if r["status"] == IR.ROUTING_RETIRED]
    # 78 -> 165: the 87 newly-recovered Cleveland routes are all
    # ROUTING_CONFIRMED; the two pre-existing Columbus holds are untouched.
    # 165 -> 163, the same two retirements.
    #
    # PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 adds one CONFIRMED and eight HELD.
    # The eight Dayton holds are a THIRD shape, and naming it is the point: the
    # operator's browser reported name, street and postal-code agreement, and
    # this work order could not read one identity key from the destination
    # itself -- choicehotels.com answered nothing at 25s and again at 60s,
    # ihg.com and redroof.com answered 403. A route bound on a transcription
    # alone is retained and visible, and it is not a work instruction.
    #
    # PTF-CENSUS-PARTITION-NORMALIZATION-001 then RETIRED two Cleveland
    # records -- Eastland Inn Restaurant (CONFIRMED) and The Welshfield Inn
    # (HELD) -- because both bind accommodation routes to identities that
    # Cleveland's 188-hotel census deliberately does not contain: a restaurant
    # and a cross-category inn. The invariant they broke is fixed by
    # withdrawing the routes, not by admitting non-hotels to a hotel census.
    # So one leaves each bucket: 164 -> 163 confirmed, 10 -> 9 held.
    # PTF-CLEVELAND-ROUTING-REPAIR-001: +3 created CONFIRMED, and Best Western Plus
    # North Canton moved CONFIRMED -> HELD because bestwestern.com
    # refuses to serve its property page (closure NOT inferred; the
    # Canton CVB lists it operating).
    # 78 -> 288: all 210 new Cincinnati routes are ROUTING_CONFIRMED (every
    # target that reached routing authority carried a verified URL with
    # street/ZIP/phone-where-available binding; nothing was written HELD).
    # held and retired are untouched by Cincinnati.
    # 288 -> 265: all 23 of Cleveland Pass 4's retirements were themselves
    # ROUTING_CONFIRMED routes (every disposed identity had a confirmed
    # binding before it published or excluded); held and retired stay 10/2.
    #
    # PTF-MARKET-AUTHORITY-SHARDING-001: derived per status from the shards for
    # the reason given on the total above. The identity assertions immediately
    # below are what actually hold the line -- WHICH records are held and
    # retired is the substance, and naming them survives a market being added.
    for status, bucket in ((IR.ROUTING_CONFIRMED, confirmed),
                           (IR.ROUTING_HELD, held),
                           (IR.ROUTING_RETIRED, retired)):
        expected = sum(1 for m in MA.sharded_market_ids()
                       for r in MA.load_market_routes(m) if r["status"] == status)
        assert len(bucket) == expected, status
    # PTF-CINCINNATI-HARDENED-SYNC-002 adds six. Cincinnati's Pass 1 retired 27
    # routes: 21 whose identity became seed inventory, and 6 whose identity
    # became a VERIFIED_NO_PETS exclusion. The 21 are GONE -- retirement is
    # removal here, and leaving them beside their seed rows is the double-source
    # the test below refuses; they are preserved verbatim in
    # cincinnati_route_retirement_002_ledger.json.
    #
    # The 6 stay, marked retired. There is no rule against routing an excluded
    # identity -- Columbus keeps 13 and Grand Rapids 15, both ROUTING_CONFIRMED
    # -- so an exclusion creates no second source of truth and nothing to
    # remove. Cincinnati simply recorded the disposition on the route as well,
    # which is a founder ruling and not this suite's to overwrite.
    assert {h["hotel_ref"]["normalized_name"] for h in retired} == {
        "eastland inn restaurant", "the welshfield inn",
        "baymont by wyndham monroe",
        "best western plus hannaford inn and suites",
        "best western premier mariemont inn",
        "days inn batavia", "days inn cincinnati east",
        "doubletree by hilton lawrenceburg",
        # PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029. Detroit arrived carrying one
        # retired route: a founder ruled the Motel 6 identity at 3764 S State St
        # closed or converted, and ROUTING_RETIRED is precisely a route to an
        # identity this market's census no longer contains.
        "motel 6 ann arbor"}
    assert {h["hotel_ref"]["normalized_name"] for h in held} == {
        "best western plus north canton inn and suites",
        "staybridge suites columbus worthington",
        "comfort suites springfield i 70",
        "holiday inn express and suites greenville",
        "quality inn greenville",
        "quality inn sidney",
        "red roof inn dayton fairborn nutter center",
        "red roof inn dayton north airport",
        "red roof inn dayton south miamisburg",
        "red roof inn springfield",
        # PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029. Not an undecided
        # binding like the others -- a POISONED one.
        # detroitriverwalkhotel.com lapsed and now redirects to an
        # online-gambling site, and the record sat at ROUTING_CONFIRMED,
        # the only status a capture queue may act on. HELD rather than
        # RETIRED: the binding was correct when made, its identity is
        # still in the census, and keeping the URL on file is how the
        # hijack stays documented.
        "roberts riverwalk hotel"}


def test_every_committed_record_preserves_index_binding(routes):
    # PTF-CLEVELAND-URL-RECOVERY-WORKER-002 landed 72 of its 87 new Cleveland
    # routes as PAGE_RENDERED, on the claim that the brands "did not refuse the
    # request this time". PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001 re-probed
    # all 72 with a browser UA and could not reproduce that: 55 answered 403 and
    # 7 (Choice/Cambria) never answered at all. Those 62 were corrected back to
    # BRAND_INDEX_BINDING, which is what their own binding_sources describe --
    # property codes and index content, not a served property page.
    #
    # The 10 that really did serve us their page are kept as PAGE_RENDERED: the
    # eight independent first-party B&B/motel sites and the two Drury
    # properties. Both methods are therefore legitimately present, but the split
    # is now evidence-backed rather than asserted.
    #
    # PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 adds the ninth. Sonesta ES
    # Suites Cleveland Airport was corrected to the Simply Suites path after the
    # rebrand, and the binding was NOT taken from the operator transcription
    # that proposed it: the recorded URL was fetched directly, returned 200,
    # 301-redirected to the replacement, and served JSON-LD carrying the
    # property's own name, street address, postal code and telephone. That is a
    # page the property served us, which is what PAGE_RENDERED means. Its
    # binding_sources carries the html_sha256 of what came back, and sonesta.com
    # is not a bot-walled brand -- so it passes the rule below rather than
    # needing an exception from it.
    assert {r["binding_method"] for r in routes} == {
        IR.BINDING_BRAND_INDEX, IR.BINDING_PAGE_RENDERED}
    rendered = [r for r in routes if r["binding_method"] == IR.BINDING_PAGE_RENDERED]
    # 10 -> 8: both retired Drury routes were PAGE_RENDERED. 8 -> 9: Sonesta.
    #
    # 9 -> 10: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 adds Golden Inn New
    # Paris, an independent property whose own site answered a plain GET and
    # served the census telephone and locality. Its eight Dayton siblings in
    # the same batch are BRAND_INDEX_BINDING for exactly the reason this test
    # exists: Choice, IHG and Red Roof refused this work order too, so nothing
    # they serve may be called a rendered page.
    # 5 after Pass 3 retired four rendered-page independents and the
    # Sonesta route; 18 after PTF-CLEVELAND-ROUTING-REPAIR-001: thirteen repaired or
    # created routes whose non-bot-walled pages rendered for this session
    # with the census identity on them (wyndhamhotels.com, sonesta.com,
    # magnusonhotels.com and nine first-party independents).
    # 18 -> 36: PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C adds 18 more --
    # independent first-party sites whose own page content bound the
    # identity (21c Museum, Golden Lamb, Great Wolf Lodge, Motel Beechmont,
    # REST, Symphony Hotel & Restaurant, The Elms, The Summit Hotel,
    # Wildwood Inn and others), none on a bot-walled brand domain.
    # 36 -> 30: six of Cleveland Pass 4's 23 retired routes were themselves
    # PAGE_RENDERED (their identities published or excluded, so the
    # rendered-page routing placeholder that got them there is retired too).
    # PTF-MARKET-AUTHORITY-SHARDING-001: derived from the shards, same reason as
    # the totals above. The assertion that carries the weight is the next one --
    # a bot-walled brand can never be the source of a rendered-page binding --
    # and it is a property of every record, not of how many there are.
    assert len(rendered) == sum(
        1 for m in MA.sharded_market_ids() for r in MA.load_market_routes(m)
        if r["binding_method"] == IR.BINDING_PAGE_RENDERED)
    # A brand that bot-walls us can never be the source of a rendered-page
    # binding. This is the assertion that would have caught the original batch.
    walled = {"hilton.com", "marriott.com", "ihg.com", "choicehotels.com",
              "bestwestern.com", "radissonhotels.com", "redroof.com",
              "extendedstayamerica.com"}
    for r in rendered:
        assert IR.registrable_domain(r["official_property_url"]) not in walled


def test_no_committed_route_is_on_a_third_party_domain(routes):
    for r in routes:
        assert IR.registrable_domain(r["official_property_url"]) \
            not in IR.NEVER_OFFICIAL_DOMAINS


def test_every_committed_route_is_in_a_known_market(routes):
    """Routing is per-market; a route must always identify a configured market.

    Keep this derived from the shard registry so a new market routing shard does
    not require a fragile, hand-maintained global market list.
    """
    expected = {market_id for market_id in MA.sharded_market_ids()
                if MA.load_market_routes(market_id)}
    assert {r["market_id"] for r in routes} == expected


def test_columbus_routing_is_unchanged_by_the_cleveland_market(routes):
    columbus = [r for r in routes if r["market_id"] == "columbus-oh"]
    assert len(columbus) == 20
    assert sum(1 for r in columbus if r["status"] == IR.ROUTING_CONFIRMED) == 19


def test_no_committed_route_is_already_seed_inventory(routes):
    seed = {normalize_name(r["name"]) for r in
            csv.DictReader((LP / "seed_businesses.csv").open(encoding="utf-8"))
            if r["category"] == "pet-friendly-hotels"}
    for r in routes:
        assert r["hotel_ref"]["normalized_name"] not in seed, (
            "%s is seed inventory; the seed remains the source of truth for it"
            % r["hotel_ref"]["normalized_name"])


# --------------------------------------------------------------------------- #
# Authority separation -- the negative guarantees
# --------------------------------------------------------------------------- #

def test_routing_does_not_enter_seed_inventory():
    rows = list(csv.DictReader((LP / "seed_businesses.csv").open(encoding="utf-8")))
    # Scoped by market: the seed is multi-market now. Columbus's 89 hotel rows
    # must be untouched by routing, which is what this has always asserted.
    hotels = [r for r in rows if r["category"] == "pet-friendly-hotels"
              and r.get("market_id") == "columbus-oh"]
    assert len(hotels) == 89, "seed hotel rows must be untouched by routing"


def test_routing_does_not_change_published_count():
    pkg = json.loads((LP / "hotel_policy_facts.json").read_text(encoding="utf-8"))
    assert len(pkg["hotels"]) == 88


def test_routing_does_not_change_the_release_held_count():
    """held is derived from the seed alone, so routing cannot move it."""
    from scripts.pettripfinder.site_data import (
        load_published_hotel_policy_facts, read_production_rows,
        verified_public_hotels,
    )
    # PTF-PER-MARKET-RELEASE-CONTRACTS-001: the release contract is per market,
    # so this assertion names the market it is about instead of reading "the"
    # contract and hoping it is Columbus's.
    contract = json.loads(
        (_REPO / "deploy" / "netlify" / "release_contracts" / "columbus-oh.json")
        .read_text(encoding="utf-8"))
    # The contract is COLUMBUS's, so held must be measured over Columbus's
    # seed. Counting every market's hotel rows reports 20 held for a market
    # that holds exactly one.
    hotel_seed = [r for r in read_production_rows()
                  if r.get("category") == "pet-friendly-hotels"
                  and r.get("market_id") == "columbus-oh"]
    verified = verified_public_hotels(
        hotel_seed, load_published_hotel_policy_facts("columbus-oh"))
    held = len(hotel_seed) - len(verified)
    # 5 -> 3: PTF-COLUMBUS-FINAL-CLOSURE-001 published two held seed rows.
    assert held == contract["public_surface"]["excluded_public_profile_count"] == 1


def test_no_publication_module_reads_the_routing_authority():
    """Structural: the publication path must not import routing at all."""
    import ast
    targets = [
        _REPO / "scripts" / "generate_pettripfinder_columbus_site.py",
        _REPO / "scripts" / "pettripfinder" / "assemble_netlify_bundle.py",
        _REPO / "scripts" / "pettripfinder" / "publication_guard.py",
        _REPO / "scripts" / "pettripfinder" / "site_data.py",
    ]
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        assert not any("identity_routing" in n for n in names), (
            "%s imports identity_routing; routing must never reach publication"
            % path.name)


# --------------------------------------------------------------------------- #
# Capture queue integration
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def queues():
    base = build_queue(batch_id="t-base", require_retrieval_artifact=False,
                       use_identity_routing=False)
    routed = build_queue(batch_id="t-routed", require_retrieval_artifact=False)
    return base, routed


@pytest.fixture(scope="module")
def routing_delta_from_shards(tmp_path_factory):
    """The capture-queue contribution routing SHOULD make, derived by asking
    each market's shard alone and adding the answers up.

    PTF-MARKET-AUTHORITY-SHARDING-001. This replaces a pinned global figure,
    and it is a stronger claim than the number it replaces: if the whole
    authority contributes exactly what the markets contribute separately, then
    no market's routes suppressed or duplicated another market's queue rows.
    A pinned total could not distinguish those cases; it could only be
    re-derived after the fact and re-typed.
    """
    base = build_queue(batch_id="t-base-per-market",
                       require_retrieval_artifact=False,
                       use_identity_routing=False)
    root = tmp_path_factory.mktemp("per-market-routing")
    total = 0
    for market_id in MA.sharded_market_ids():
        document = MA.build_routing_shard(market_id, MA.load_market_routes(market_id))
        path = root / ("%s.json" % market_id)
        path.write_text(MA.render_json(document), encoding="utf-8")
        alone = build_queue(batch_id="t-%s" % market_id,
                            require_retrieval_artifact=False,
                            routing_path=path)
        total += len(alone.selected) - len(base.selected)
    return total


def test_routing_adds_capture_ready_hotels(queues, routing_delta_from_shards):
    base, routed = queues
    assert len(routed.selected) > len(base.selected)
    # Was 16, then 10, then 1. PTF-NEGATIVE-EVIDENCE-P0-001 applied five more
    # VERIFIED_NO_PETS exclusions, and an identity already answered by evidence
    # is no longer capture-worthy -- so routing's Columbus contribution fell to
    # the hotels still genuinely awaiting a policy. The number falling as hotels
    # get ANSWERED is the queue working, not routing regressing.
    #
    # PTF-CLEVELAND-MARKET-FACTORY-001: routing now carries a whole second
    # market and the number jumps to 39. Cleveland's census is 193 CONFIRMED
    # non-inventory hotels -- precisely the situation routing exists for -- and
    # 87 of them now hold an official URL recovered from their CVB listing.
    #
    # It was 29 until Marriott's short property link (marriott.com/cleac) was
    # taught to the URL-shape classifier; ten more Cleveland hotels had a real
    # official URL that read as UNKNOWN. Columbus's own contribution is
    # unchanged at 1.
    # 39 -> 12: Cleveland's routed contribution fell as its hotels were
    # ANSWERED. 19 became inventory and 8 became verified-no-pets, so their
    # routes retired and they are no longer capture-worthy. The number falling
    # because hotels got answered is the queue working, not routing regressing.
    # 12 -> 86: PTF-CLEVELAND-URL-RECOVERY-WORKER-002 recovered 87 more
    # official URLs for hotels that were previously NO_OFFICIAL_URL and so
    # invisible to the queue; 74 of those 87 are for brands this registry
    # already adapts and became capture-eligible, and Columbus's own
    # contribution is unchanged.
    # 86 -> 84: two routed hotels became inventory and no longer need a
    # route to reach the capture queue.
    # 26 -> 168: PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C opened Cincinnati
    # routing (210 new routes). 142 of them are capture-shaped -- a
    # registered brand adapter plus an https official URL -- broken down by
    # brand: hilton 49, marriott 27, choice 21, ihg 15, wyndham 13,
    # redroof 6, bestwestern 5, extendedstay 4, drury 2 (=142, isolated by
    # re-running the queue with Cincinnati's routes filtered out and
    # diffing). The other 68 (the 40 independents plus lanes this registry
    # does not adapt) are retained in identity_routing.json as real routing
    # but are not yet capture-eligible.
    # 168 -> 148: PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 retired 23
    # Cleveland routing placeholders as their identities published or were
    # excluded; a route that no longer exists cannot add a queue row, and
    # this rerun of the queue against the merged routing authority is the
    # derivation for the new delta.
    # PTF-MARKET-AUTHORITY-SHARDING-001: derived from the per-market shards
    # rather than pinned. See the routing_delta_from_shards fixture.
    assert len(routed.selected) - len(base.selected) == routing_delta_from_shards


def test_routing_carries_more_than_one_market(queues, routing_delta_from_shards):
    """The guarantee that matters now routing is not Columbus-only: the second
    market's routes are real queue rows, and the first market's contribution is
    untouched by their arrival."""
    from scripts.pettripfinder.identity_routing import load_routes
    by_market = {}
    for r in load_routes():
        by_market.setdefault(r["market_id"], []).append(r)
    assert len(by_market["columbus-oh"]) == 20
    # 87 -> 60: publishing 19 Cleveland hotels and excluding 8 retired their
    # routes, because routing is only for hotels that are NOT inventory.
    # 60 -> 147: PTF-CLEVELAND-URL-RECOVERY-WORKER-002 recovered official URLs
    # for 87 of the 102 hotels classified NO_OFFICIAL_URL.
    # 147 -> 145, the same two retirements.
    # 38 after PTF-CLEVELAND-ROUTING-REPAIR-001; unchanged at 38 through
    # PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001, whose 23 retirements
    # came entirely from the pre-repair 61 placeholders those decisions
    # settled -- the repair-created routes were not among them.
    assert len(by_market["cleveland-akron-canton-oh"]) == 38
    assert len(by_market["dayton-oh"]) == 9
    # First-time Cincinnati routing: 223 targets adjudicated, 210 routed (12
    # ROUTING_UNRESOLVED and 1 PROPERTY_CLOSED_OR_CONVERTED-with-no-URL
    # excluded -- see PTF-CINCINNATI-URL-ROUTING-RECOVERY-001C).
    # 210 -> 189: PTF-CINCINNATI-HARDENED-SYNC-002 removed the 21 routes whose
    # identity had become seed inventory. Pass 1 had marked them
    # ROUTING_RETIRED and left them in place, which is not what retirement
    # means here -- Cleveland's 23 took its own total from 288 to 265 -- and
    # left Cincinnati as the only market with a route for a published hotel.
    # 189 -> 135 at PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004: three
    # routes retired because their URL no longer resolves to the hotel (two
    # lapsed domains resold to unrelated sites, one property page that became a
    # brand search page), and 51 removed on the same seed-inventory rule when
    # the founder's Capture Pass 3 block published their identities.
    # 135 -> 94 at PTF-CINCINNATI-FREE-LANE-APPLICATION-007, which withdrew
    # the 41 routes its own application answered. One route it could have
    # withdrawn was deliberately kept: Comfort Suites MainStay was ruled
    # HOLD_FOR_IDENTITY_REVIEW, and a withdrawn route is how a row stops being
    # worked.
    # 94 -> 79 at PTF-CINCINNATI-FREE-LANE-APPLICATION-010, which withdrew
    # the 15 routes its own application answered. Studio 6 was ruled
    # HOLD_FOR_IDENTITY_ADDRESS_CLARIFICATION and deliberately kept its route.
    # -> 80 at PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013, which replaced the conflated MainStay route with one
    # route per real property.
    assert len(by_market["cincinnati-oh"]) == 80

    base, routed = queues
    base_ids = {h["hotel_id"] for h in base.selected}
    added = [h for h in routed.selected if h["hotel_id"] not in base_ids]
    # 39 -> 12: Cleveland's routed contribution fell as its hotels were
    # ANSWERED -- 19 became inventory and 8 became verified-no-pets, so their
    # routes retired and they are no longer capture-worthy.
    # 12 -> 86: 74 of the 87 newly-recovered routes are capture-shaped
    # (registered brand adapter + https official URL); the other 13 -- mostly
    # independent B&Bs/motels and brands this registry does not adapt
    # (Motel 6, Extended Stay America, Radisson, Sonesta ABVI, Knights Inn) --
    # are retained in identity_routing.json as real routing but are not yet
    # capture-eligible.
    # 86 -> 84: PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 answered two of
    # those 74 (the Drury pair), so their routes retired and they reach the
    # queue as inventory rather than as routing.
    # 26 -> 168: Cincinnati's first routing pass contributes 142 capture-shaped
    # rows (see test_routing_adds_capture_ready_hotels for the per-brand
    # split); Cleveland and Columbus are unchanged.
    # 168 -> 148: PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001's 23 route
    # retirements remove their contribution to the capture-ready set; the
    # exact new figure is the rerun against the merged routing authority,
    # same derivation as test_routing_adds_capture_ready_hotels above.
    # PTF-MARKET-AUTHORITY-SHARDING-001: derived, same fixture, same reason.
    assert len(added) == routing_delta_from_shards
    # Every added row is capture-shaped: a brand with a registered adapter and
    # an official URL. A row that cannot be captured is not a contribution.
    for h in added:
        assert h["brand"], h["hotel_id"]
        assert h["official_url"].startswith("https://"), h["hotel_id"]


def test_previously_usable_seed_urls_remain_usable(queues):
    base, routed = queues
    base_ids = {h["hotel_id"] for h in base.selected}
    routed_ids = {h["hotel_id"] for h in routed.selected}
    assert base_ids <= routed_ids, "routing must never remove a seed-sourced entry"


def test_seed_url_takes_precedence_over_routing(tmp_path):
    """A seed row that HAS a URL keeps it, even if routing knows another."""
    seed = tmp_path / "seed.csv"
    with seed.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "name", "category", "address", "city", "state", "postal_code",
            "phone", "website_url", "source_url", "source_type", "observed_at",
            "rating", "amenities", "pet_policy", "canonical"])
        w.writeheader()
        w.writerow({"name": "Sample Inn Columbus", "category": "pet-friendly-hotels",
                    "address": "1 Test St", "city": "Columbus", "state": "OH",
                    "postal_code": "43215", "phone": "614-555-0100",
                    "website_url": "https://www.marriott.com/en-us/hotels/seed1-sample/overview/"})
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record(
        official_property_url="https://www.marriott.com/en-us/hotels/route1-sample/overview/",
        property_code="ROUTE1",
        identity_context={"address": "1 Test St", "city": "Columbus",
                          "state": "OH", "postal_code": "43215",
                          "phone": "614-555-0100"}))), encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    urls = [h["official_url"] for h in result.selected]
    assert urls == ["https://www.marriott.com/en-us/hotels/seed1-sample/overview/"]


def test_routing_fills_in_when_the_seed_url_is_absent(tmp_path):
    seed = tmp_path / "seed.csv"
    with seed.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "name", "category", "address", "city", "state", "postal_code",
            "phone", "website_url", "source_url", "source_type", "observed_at",
            "rating", "amenities", "pet_policy", "canonical"])
        w.writeheader()
        w.writerow({"name": "Sample Inn Columbus", "category": "pet-friendly-hotels",
                    "address": "1 Test St", "city": "Columbus", "state": "OH",
                    "postal_code": "43215", "phone": "614-555-0100",
                    "website_url": ""})
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record())), encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    assert [h["official_url"] for h in result.selected] == [
        "https://www.marriott.com/en-us/hotels/xxxxx-sample/overview/"]
    assert "identity routing" in result.selected[0]["notes"]


def test_a_held_route_is_never_used(routes, queues):
    _, routed = queues
    held = [r for r in routes if r["status"] != IR.ROUTING_CONFIRMED]
    queued = {h["listing_key"] for h in routed.selected}
    for r in held:
        assert r["hotel_ref"]["normalized_name"] not in queued


def test_a_weak_binding_is_not_confirmed(routes):
    weak = [r for r in routes
            if r["hotel_ref"]["normalized_name"] == "staybridge suites columbus worthington"]
    assert weak and weak[0]["status"] == IR.ROUTING_HELD


def test_routing_record_without_queue_identity_is_excluded_not_invented(tmp_path):
    routing = tmp_path / "routing.json"
    routing.write_text(json.dumps(authority(record(
        identity_context={"city": "Columbus"}))), encoding="utf-8")
    seed = tmp_path / "seed.csv"
    seed.write_text("name,category,address,city,state,postal_code,phone,website_url,"
                    "source_url,source_type,observed_at,rating,amenities,pet_policy,"
                    "canonical\n", encoding="utf-8")
    result = build_queue(batch_id="t", seed_csv=str(seed), routing_path=str(routing),
                         require_retrieval_artifact=False)
    assert result.selected == ()
    assert any("routing_identity_incomplete" in e.reason for e in result.excluded)


def test_queue_entry_from_routing_carries_no_policy_fact(queues):
    _, routed = queues
    for hotel in routed.selected:
        assert "pet_policy" not in hotel
        assert "pets_allowed" not in hotel


def test_disabling_routing_restores_the_prior_queue(queues):
    base, _ = queues
    # 77 was the Columbus-only figure. Cleveland's published inventory now adds
    # its own capture-eligible rows to the unrouted queue as well; what the test
    # protects is that turning routing OFF still yields the smaller, seed-only
    # queue, not an exact single-market total.
    _, routed = queues
    assert len(base.selected) < len(routed.selected)
    assert len(base.selected) >= 77
