"""PETTRIPFINDER-PROD-004 Stage B — verified-only public generation + evidence links.

Proves public hotel generation is restricted to the 14 committed-package hotels
(the 11 held/manual-review hotels get no public route on any surface), every
verified profile exposes its exact committed policy source_url as a distinct
evidence link, and matching is deterministic and fail-closed. The build-level
tests run the real generator into a temp dir (the launch package and seed CSV are
committed, so they run in a clean clone); nothing writes to production.
"""

from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path

import pytest

from scripts.pettripfinder.site_data import (
    normalize_name, read_production_rows, verified_public_hotels,
)

_REPO = Path(__file__).resolve().parents[2]
_PKG = json.loads((_REPO / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json").read_text(encoding="utf-8"))
_PKG_KEYS = {h["key"] for h in _PKG["hotels"]}
# PTF-COLUMBUS-FINAL-CLOSURE-001: both Red Roofs left this list once their
# URLs parsed a property code, which gave the identity gate a second key
# group and let the attended browser reach their pet policies.
# PTF-COLUMBUS-SELECTOR-CLOSEOUT-001: Drury Plaza left it too. See the note
# below -- the URL that was thought to serve a different property now redirects
# to this one, and two attended runs confirmed the identity on it.
# PTF-COLUMBUS-HYATT-002: Hyatt House Short North left this list on
# operator-supplied official-page screenshots -- the lawful route for a brand
# whose bot defence ADR-PTF-AUTOMATED-BROWSING forbids us to satisfy.
_HELD = [
    "extended-stay-america-suites-columbus-dublin",
    "hyatt-place-columbus-polaris",
]
# PTF-PROMOTION: sonesta-simply-suites-dublin-columbus left this list on
# 2026-08-02. Its only remaining Gate-1 reason was a MODEL_OVERCLAIM -- the
# model proposed a dogs value the official page never supports, and the airlock
# rejected and removed it -- so it was approved under
# APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT, which acknowledges the diagnostic
# rather than waiving a defect. It publishes pets_allowed, a 2-pet limit, no
# breed restriction and a two-tier fee ladder ($75 nights 1-7 per pet, $150
# nights 8+); its explicit "cats are not permitted" is preserved in promotion
# provenance because species_allowed is a positive list with no way to express
# an exclusion, so the profile under-claims rather than mis-states. Dogs stay
# NOT_STATED: the page never uses the word.
# PTF-DATA: both Columbus La Quinta properties left this list on 2026-08-02.
# Their pages answer ordinary retrieval with HTTP 200 but do not carry the
# policy VALUES, which exist only after rendering -- PTF-CAPTURE-004A gave that
# state its own classification (RENDER_REQUIRED), 004B captured them, 004C made
# the evidence complete, and both were attested and approved. Each fee is
# published under an explicit structured resolution of the page-wide
# conflicting_fee_basis markers (APR-LAQ-WEST-HILLIARD-001, APR-LAQ-DUBLIN-001);
# the markers themselves remain on the attestations.
# PTF-INVENTORY-001: red-roof-plus-columbus-downtown-convention-center left this
# list on 2026-07-28. It was promoted under an explicit APPROVED_TIERED_FEE_OMITTED
# decision -- its Gate-1 block was solely a tiered fee the scalar schema cannot
# render, and it now publishes with the fee field omitted rather than flattened.
#
# PTF-CAPTURE-003F: aloft-columbus-university-district left this list on
# 2026-08-01. Its automated retrieval was blocked (403), so it was attested
# from a visible-browser capture and approved under APR-ALOFT-CMHCO-001. The
# approver's recorded judgement: the page-wide amounts 100/150/50 are a Bonvoy
# promo and a guest review, not conflicting pet-policy terms -- the Pets card
# itself states $50 per night with a $150 per-stay maximum, which are
# complementary.
#
# PTF-PROMOTE: staybridge-suites-columbus-dublin left this list on 2026-08-01.
# Its policy is stated in prose rather than labelled fields, so nothing about it
# was readable until the prose reader existed. It now publishes species, count
# and weight, with its fee withheld under
# unrepresentable_fee_range_in_official_source -- the source gives "75 to 150
# dollars depending on length of stay", which no single figure can carry.
#
# --------------------------------------------------------------------------- #
# PTF-INVENTORY triage, 2026-08-02 (operator rule: anything needing more than
# ~15 minutes of bespoke work is held rather than carried as open work).
#
# Every entry above this line records a hotel that LEFT the list. The four
# below record why hotels REMAIN on it, so a future reader does not have to
# re-derive a blocker that was already investigated and priced.
#
# HELD -- red-roof-inn-columbus-west-hilliard. Its Gate-1 record carries
# INCOMPLETE_EXTRACTION and SOURCE_AUTHORITY_AMBIGUITY on top of the tiered fee,
# and both are never-waivable. Its sibling Worthington shed exactly those codes
# on a re-run, so a refresh is plausible -- but the seed also carries NO PHONE
# for this property, which is an identity gap a re-run cannot close.
#
# RELEASED -- drury-plaza-hotel-columbus-downtown, by
# PTF-COLUMBUS-SELECTOR-CLOSEOUT-001. The hold was correct when it was made and
# the world moved: the seed's URL
# (/locations/columbus-oh/drury-inn-and-suites-columbus-convention-center) no
# longer serves 640 Marconi Blvd, it 301s to
# /locations/columbus-oh/drury-plaza-hotel-columbus-downtown. Two independent
# attended runs followed it there and both identity gates CONFIRMED 88 East
# Nationwide Blvd / 614-221-7008, so the seed row now records the redirect
# target directly. The remaining blocker was never extraction: the policy sits
# in a shut #additional-info-modal, and one grounded click opened it.
#
# HELD -- extended-stay-america-suites-columbus-dublin. The only Columbus hotel
# with NO retrieval artifact of any kind, so its access posture is unmeasured.
# Its fee is "up to $25 per day per pet for the first six nights, then up to
# $15 per day": a word-number boundary and a "then" rate the tier parser cannot
# represent, and its Gate-1 block is CONTRADICTORY_OFFICIAL_SOURCES, which is
# never waivable. Two live extraction hazards are also recorded against this
# wording (a flattened $25 scalar and a rate ceiling misread as a stay cap);
# both are contained by the PTF-FEE-TIERS-005 guard, neither is fixed.
#
# HELD (indefinitely) -- hyatt-house-columbus-osu-short-north. hyatt.com serves
# a Kasada bot-defence interstitial that never resolves, measured even in a
# visible browser, and ADR-PTF-AUTOMATED-BROWSING forbids satisfying it.
# services/research_workers/capture_automation/adapters/registry.py refuses to
# register a Hyatt adapter for this reason. Its Gate-1 block is independently
# CONTRADICTORY_OFFICIAL_SOURCES ($100 vs $75; 50 pounds each vs 75 combined).
# This one is not waiting on effort; it is waiting on a policy change we have
# declined to make.
#
# NOT triaged as held -- sonesta-simply-suites-dublin-columbus and
# red-roof-plus-columbus-dublin are the next batch candidates. Each needs one
# worker run and a Gate-1 refresh, no new architecture. Sonesta already has an
# authorised APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT decision waiting on a
# current result_hash to bind to. They remain in this list only because nothing
# is published until it is promoted.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Deterministic, fail-closed verified-only join (self-contained).
# --------------------------------------------------------------------------- #

def test_verified_public_hotels_selects_only_package_matches_in_seed_order():
    rows = [{"name": "A Hotel", "category": "pet-friendly-hotels"},
            {"name": "B Hotel", "category": "pet-friendly-hotels"},
            {"name": "Held Hotel", "category": "pet-friendly-hotels"}]
    verified = verified_public_hotels(rows, {"a hotel": {}, "b hotel": {}})
    assert [r["name"] for r in verified] == ["A Hotel", "B Hotel"]   # order preserved, Held excluded


def test_verified_public_hotels_fails_closed_on_unmatched_policy_record():
    with pytest.raises(ValueError):
        verified_public_hotels([{"name": "A Hotel"}], {"a hotel": {}, "missing hotel": {}})


def test_verified_public_hotels_fails_closed_on_ambiguous_display_match():
    with pytest.raises(ValueError):
        verified_public_hotels([{"name": "A Hotel"}, {"name": "A  Hotel"}], {"a hotel": {}})


def test_committed_package_matches_a_seed_display_row_for_every_record():
    hotel_rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    pf = {h["key"]: h for h in _PKG["hotels"]}
    verified = verified_public_hotels(hotel_rows, pf)   # must not raise
    assert len(verified) == 88


# --------------------------------------------------------------------------- #
# Renderer evidence link (self-contained).
# --------------------------------------------------------------------------- #

def test_renderer_exposes_exact_source_url_as_distinct_evidence_link():
    from scripts.pettripfinder.hotel_profile import build_vm_from_production, _prov_html
    row = {"name": "Test Hotel", "city": "Columbus", "state": "OH", "address": "1 Main St",
           "postal_code": "43215", "website_url": "https://brand.example/", "phone": "",
           "observed_at": "2026-07-15"}
    facts_entry = {"facts": {"pets_allowed": "true", "species_allowed": "dogs"},
                   "verified_at": "2026-07-15", "evidence_quote": "Dogs accepted",
                   "source_url": "https://official.example/policies?a=1&b=2"}
    vm = build_vm_from_production(row, facts_entry, [], {})
    assert vm.source_url == "https://official.example/policies?a=1&b=2"
    prov = _prov_html(vm)
    assert "View the official pet-policy source" in prov
    assert "https://official.example/policies?a=1&amp;b=2" in prov     # exact URL, HTML-escaped
    assert 'rel="nofollow noopener external"' in prov and 'target="_blank"' in prov
    evidence_block = prov.split("fh-evidence")[1].split("</div>")[0]
    assert "/go/" not in evidence_block                                # direct citation, not the /go/ CTA


def test_renderer_omits_evidence_link_without_source_url():
    from scripts.pettripfinder.hotel_profile import build_vm_from_production, _prov_html
    row = {"name": "Test Hotel", "city": "Columbus", "state": "OH", "address": "1 Main St",
           "postal_code": "43215", "website_url": "https://brand.example/", "phone": "", "observed_at": "2026-07-15"}
    vm = build_vm_from_production(row, {"facts": {"pets_allowed": "true"}, "verified_at": "2026-07-15"}, [], {})
    assert vm.source_url == ""
    assert "fh-evidence-link" not in _prov_html(vm)


# --------------------------------------------------------------------------- #
# Build-level: the real generator into a temp dir (committed inputs only).
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def build(tmp_path_factory):
    from scripts.generate_pettripfinder_columbus_site import run
    out = tmp_path_factory.mktemp("prod004_vbuild") / "site"
    run(str(out))
    return out


def _hotel_slugs(build):
    # PTF-CORRIDORS-002: corridor pages are config-driven, so the non-profile
    # directory set is derived from the committed market config.
    from scripts.pettripfinder.market_context import production_market
    non = {"policy-comparison"} | {
        c.slug for c in production_market().corridors}
    return sorted(
        os.path.relpath(f, build).replace(os.sep, "/").split("/")[1]
        for f in glob.glob(str(build) + "/pet-friendly-hotels/*/index.html")
        if len(os.path.relpath(f, build).split(os.sep)) == 3
        and os.path.relpath(f, build).replace(os.sep, "/").split("/")[1] not in non)


def _display_slug(key):
    disp = {normalize_name(r["name"]): r["name"] for r in read_production_rows()
            if r["category"] == "pet-friendly-hotels"}
    return re.sub(r"[^a-z0-9]+", "-", disp[key].strip().lower()).strip("-")


def test_exactly_the_committed_public_hotel_profiles(build):
    assert len(_hotel_slugs(build)) == 88


def test_every_profile_belongs_to_the_committed_package(build):
    pkg_slugs = {_display_slug(k) for k in _PKG_KEYS}
    assert set(_hotel_slugs(build)) == pkg_slugs


def test_all_held_hotels_have_no_public_profile(build):
    slugs = set(_hotel_slugs(build))
    assert not (slugs & set(_HELD))
    # Named separately so a single promotion cannot empty the assertion
    # unnoticed. Drury Plaza held this spot until it was published; Hyatt
    # House is ADR-blocked and is not going anywhere soon.
    assert "extended-stay-america-suites-columbus-dublin" not in slugs


def test_excluded_hotels_absent_from_every_surface(build):
    for f in glob.glob(str(build) + "/**/*", recursive=True):
        if not os.path.isfile(f):
            continue
        try:
            text = Path(f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for ex in _HELD:
            assert ("/pet-friendly-hotels/%s/" % ex) not in text, "%s links %s" % (f, ex)
            assert ("/go/%s/" % ex) not in text


def test_all_14_verified_hotels_reachable_with_exact_source_url(build):
    pkg = {h["key"]: h for h in _PKG["hotels"]}
    import html as H
    for key, h in pkg.items():
        page = build / "pet-friendly-hotels" / _display_slug(key) / "index.html"
        assert page.exists()
        txt = page.read_text(encoding="utf-8")
        m = re.search(r'hp-evidence-link[^>]*href="([^"]+)"', txt)
        assert m and H.unescape(m.group(1)) == h["source_url"]         # exact committed source_url
        assert ("/go/%s/official-website/" % _display_slug(key)) in txt  # business CTA remains, separate


def test_no_runtime_paths_or_credentials_render(build):
    blob = "".join(Path(f).read_text(encoding="utf-8")
                   for f in glob.glob(str(build) + "/**/index.html", recursive=True) if os.path.isfile(f))
    for bad in ("worker_runs", "data/import", "columbus_worker_promotion", "candidate_id",
                "sk-live", "api_key", "bearer ey"):
        assert bad not in blob


def test_park_and_restaurant_routes_unchanged(build):
    parks = glob.glob(str(build) + "/pet-friendly-parks/*/index.html")
    restaurants = glob.glob(str(build) + "/pet-friendly-restaurants/*/index.html")
    # 14 parks + 13 restaurants (their per-listing profiles, excluding the category index)
    assert len([p for p in parks if len(os.path.relpath(p, build).split(os.sep)) == 3]) == 14
    assert len([r for r in restaurants if len(os.path.relpath(r, build).split(os.sep)) == 3]) == 13


def test_hotels_retain_placeholder_no_misattached_media(build):
    # DESIGN-004: the founder-approved profile design carries a large media
    # slot filled with the approved TEMPORARY review imagery. The honesty
    # invariant survives in its new form: the slot is always explicitly
    # captioned as temporary preview imagery -- never silently presented as
    # the property's own photo -- and no cross-category demo media appears.
    # (Licensed Google Places media is a separate, later-approved phase.)
    for slug in _hotel_slugs(build):
        txt = (build / "pet-friendly-hotels" / slug / "index.html").read_text(encoding="utf-8")
        assert "Temporary preview imagery" in txt            # explicit caption
        assert "park-demo.png" not in txt and "dining-demo.png" not in txt   # no cross-category media


def test_build_is_deterministic(tmp_path_factory):
    from scripts.generate_pettripfinder_columbus_site import run
    a = tmp_path_factory.mktemp("da") / "s"
    b = tmp_path_factory.mktemp("db") / "s"
    run(str(a))
    run(str(b))

    def man(root):
        return {os.path.relpath(f, root).replace(os.sep, "/"): Path(f).read_bytes()
                for f in glob.glob(str(root) + "/**", recursive=True) if os.path.isfile(f)}
    assert man(a) == man(b)
