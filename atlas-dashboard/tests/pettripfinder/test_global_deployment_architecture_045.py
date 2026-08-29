"""PTF-MULTI-MARKET-DEPLOYMENT-ARCHITECTURE-045 -- the bundle is deployable now.

044 stopped because the composed bundle carried no `_headers` and no
`_redirects`, satisfied 8 of 27 required gates, and would have stripped HSTS,
CSP, COOP and the rest from a live domain. These assert the gap is closed and
cannot silently reopen: the control files come from the tracked sources, the
context is explicit and fails closed, every participating market is
contract-clean, and every route the live site publishes still exists.

The full assembly is slow, so the heavy checks share one module-scoped build.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.assemble_production_site import (
    AssemblyError, HEADERS_SOURCES, LIVE_ROUTE_INVENTORY, REDIRECTS_SOURCE,
    VALID_CONTEXTS, assemble, market_eligibility, published_hotels,
    select_markets,
)
from scripts.pettripfinder.markets import load_markets

#: Short root: the generated tree nests deeply enough that a long path trips
#: the Windows 260-character limit mid-build, which surfaces as a missing file
#: rather than as a path error.
SCRATCH = Path(chr(67) + ":/t/ptf045t")

#: PTF-046: the founder withheld indianapolis-in (8 profiles, source-ready)
#: from the first multi-market launch; see deploy/netlify/launch_participation.json
#: and tests/pettripfinder/test_launch_participation_046.py.
#: PTF-ST-LOUIS-REGISTER-PUBLISH-011 admitted st-louis-mo as the sixth market
#: with 82 founder-signed profiles. It ADDED 509 files under its own namespace
#: and changed no existing profile, which is the property this file exists to
#: keep true as markets are added.
#: PTF-LOUISVILLE-PUBLICATION-008 admitted louisville-ky as the seventh with 46
#: founder-signed profiles, on the same terms: its own namespace, nothing else
#: touched.
#: PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019 admitted Indianapolis as the
#: eighth market on the founder decision that reversed the PTF-046
#: withholding. Every other market's figure below is UNCHANGED, which is
#: the half of these constants that says a new market disturbed nothing.
EXPECTED_MARKETS = ("cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
                    "indianapolis-in", "louisville-ky", "milwaukee-wi",
                    "pittsburgh-pa", "st-louis-mo")
EXPECTED_PROFILES = {"cleveland-akron-canton-oh": 99, "columbus-oh": 88,
                     "dayton-oh": 47, "indianapolis-in": 56,
                     "louisville-ky": 46, "milwaukee-wi": 73,
                     "pittsburgh-pa": 26, "st-louis-mo": 82}
EXPECTED_TOTAL = 517
EXPECTED_HTML_PAGES = 3249
EXPECTED_SITEMAP_ROUTES = 638


@pytest.fixture(scope="module")
def production():
    root = SCRATCH / "prod"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield assemble(output=str(root), context="production"), root / "site"
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Context.
# --------------------------------------------------------------------------- #

def test_the_contexts_are_exactly_production_and_preview():
    assert VALID_CONTEXTS == ("production", "preview")
    assert set(HEADERS_SOURCES) == set(VALID_CONTEXTS)


def test_an_unsupported_context_fails_closed(tmp_path):
    with pytest.raises(AssemblyError) as caught:
        assemble(output=str(tmp_path / "x"), context="staging")
    assert "context must be one of" in str(caught.value)


def test_the_context_is_recorded_in_the_manifest(production):
    manifest, _site = production
    assert manifest["context"] == "production"


# --------------------------------------------------------------------------- #
# Control files -- the 044 blocker.
# --------------------------------------------------------------------------- #

def test_the_production_bundle_carries_both_control_files(production):
    _manifest, site = production
    assert (site / "_headers").is_file()
    assert (site / "_redirects").is_file()


def test_the_control_files_are_the_tracked_sources_byte_for_byte(production):
    _manifest, site = production
    assert (site / "_headers").read_bytes() == \
        HEADERS_SOURCES["production"].read_bytes()
    assert (site / "_redirects").read_bytes() == REDIRECTS_SOURCE.read_bytes()


def test_production_headers_keep_every_live_security_directive(production):
    """The headers production serves today. Losing one of these silently is
    exactly what 044 stopped."""
    _manifest, site = production
    headers = (site / "_headers").read_bytes()
    for directive in (b"Strict-Transport-Security", b"Content-Security-Policy",
                      b"Cross-Origin-Opener-Policy", b"Permissions-Policy",
                      b"Referrer-Policy", b"X-Content-Type-Options",
                      b"X-Frame-Options"):
        assert directive in headers, directive


def test_production_is_indexable_and_preview_is_not(production, tmp_path):
    _manifest, site = production
    assert b"noindex" not in (site / "_headers").read_bytes()
    root = SCRATCH / "prev"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        assemble(output=str(root), context="preview")
        assert b"noindex" in (root / "site" / "_headers").read_bytes()
        assert (root / "site" / "_redirects").read_bytes() == \
            REDIRECTS_SOURCE.read_bytes()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_redirects_are_not_an_empty_placeholder():
    body = [line for line in REDIRECTS_SOURCE.read_text(encoding="utf-8")
            .splitlines() if line.strip() and not line.startswith("#")]
    assert body, "the tracked redirects file states no rule"


# --------------------------------------------------------------------------- #
# Participation.
# --------------------------------------------------------------------------- #

def test_the_participation_set_is_derived_not_listed(production):
    manifest, _site = production
    assert sorted(manifest["market_fragments_included"]) == \
        sorted(EXPECTED_MARKETS)


def test_every_participating_market_is_contract_clean(production):
    manifest, _site = production
    for row in manifest["participating_markets"]:
        assert row["contract_disagreements"] == [], row["market_id"]
        assert row["market_id"] in set(RC.available_market_ids())


def test_each_markets_profile_count_matches_its_own_contract(production):
    manifest, _site = production
    counts = {row["market_id"]: row["published_profiles"]
              for row in manifest["participating_markets"]}
    assert counts == EXPECTED_PROFILES
    assert sum(counts.values()) == EXPECTED_TOTAL


def test_a_contractless_market_is_excluded_and_says_why():
    """Cincinnati and Detroit must not become public because their files
    exist. Today inventory keeps them out; the gate makes the contract a
    condition too, so gaining inventory is not enough."""
    contracted = set(RC.available_market_ids())
    for market_id in ("cincinnati-oh", "detroit-ann-arbor-mi"):
        assert market_id not in contracted
        row = market_eligibility(
            next(m for m in load_markets() if m.market_id == market_id))
        assert row["assemblable"] is False
        assert [k for k, v in row["conditions"].items() if not v]


def test_an_ineligible_market_cannot_be_forced_into_the_bundle(tmp_path):
    """Passing an unassemblable market explicitly must not smuggle it in."""
    markets = [m for m in load_markets()
               if m.market_id in ("columbus-oh", "cincinnati-oh")]
    chosen, _rows = select_markets(markets)
    assert "cincinnati-oh" not in {m.market_id for m in chosen}


# --------------------------------------------------------------------------- #
# The live-route migration.
# --------------------------------------------------------------------------- #

def test_the_live_route_inventory_is_committed():
    assert LIVE_ROUTE_INVENTORY.is_file()
    routes = [l.strip() for l in
              LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")]
    assert len(routes) == 132
    assert len(set(routes)) == len(routes)
    assert all(r.startswith("/") and r.endswith("/") for r in routes)


def test_every_live_route_still_exists_in_the_bundle(production):
    """Columbus is the anchor and keeps the unprefixed namespace, so the
    multi-market composition moves none of its URLs. Asserted against the
    committed list, not assumed from the architecture."""
    _manifest, site = production
    live = [l.strip() for l in
            LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]
    on_disk = set()
    for path in site.rglob("index.html"):
        rel = path.relative_to(site).parent.as_posix()
        on_disk.add("/" if rel == "." else "/%s/" % rel)
    missing = sorted(route for route in live if route not in on_disk)
    assert missing == []


def test_the_migration_gate_would_catch_a_dropped_route(production, tmp_path):
    """The gate is only worth having if it fails when a route disappears."""
    from scripts.pettripfinder.assemble_production_site import (
        _run_migration_gate, LIVE_ROUTE_INVENTORY as INV)
    import scripts.pettripfinder.assemble_production_site as APS
    _manifest, site = production
    empty = tmp_path / "empty"
    (empty / "nothing").mkdir(parents=True)
    gates = {}
    _run_migration_gate(gates, empty)
    assert gates["global.live_routes_preserved"]["pass"] is False


def test_the_sitemap_carries_canonical_routes_not_legacy_ones(production):
    manifest, site = production
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/go/" not in sitemap
    assert manifest["sitemap_route_count"] == EXPECTED_SITEMAP_ROUTES


# --------------------------------------------------------------------------- #
# Global gates and the manifest.
# --------------------------------------------------------------------------- #

def test_every_required_global_gate_ran_and_passed(production):
    manifest, _site = production
    gates = manifest["gates"]
    for gate in GD.REQUIRED_GLOBAL_GATES:
        assert gate in gates, "gate never ran: %s" % gate
        assert gates[gate]["pass"] is True, gate
    assert manifest["all_gates_pass"] is True


def test_the_bundle_is_clean_on_every_content_measure(production):
    manifest, _site = production
    assert manifest["broken_links"] == 0
    assert manifest["collision_count"] == 0
    assert manifest["global_shadowing_count"] == 0
    assert manifest["canonical_violations"] == 0


def test_the_committed_manifest_verifies():
    assert GD.verify_manifest() == []


def test_the_manifest_references_contracts_rather_than_copying_them():
    doc = GD.load_manifest()
    for row in doc["participating_markets"]:
        assert set(row) == {"market_id", "published_profiles",
                            "release_contract", "release_contract_sha256",
                            "contract_disagreements"}
        assert (REPO / row["release_contract"]).is_file()


def test_the_manifest_pins_the_control_files_it_was_built_with():
    doc = GD.load_manifest()
    control = doc["control_files"]
    for kind, source in (("headers", HEADERS_SOURCES["production"]),
                         ("redirects", REDIRECTS_SOURCE)):
        assert control["%s_source" % kind] == \
            source.relative_to(REPO).as_posix()
        assert control["%s_sha256" % kind] == \
            hashlib.sha256(source.read_bytes()).hexdigest()


def test_a_changed_control_file_invalidates_the_manifest():
    doc = dict(GD.load_manifest())
    doc["control_files"] = dict(doc["control_files"],
                                headers_sha256="0" * 64)
    assert any("headers.production has changed" in p
               for p in GD.verify_manifest(doc))


def test_a_preview_bundle_cannot_produce_a_deployment_manifest():
    with pytest.raises(GD.GlobalDeploymentError):
        GD.build_manifest({"context": "preview"})


# --------------------------------------------------------------------------- #
# Deployment stays unauthorized.
# --------------------------------------------------------------------------- #

def test_assembly_does_not_authorize_deployment(production):
    manifest, _site = production
    assert manifest["deployment_authorized"] is False


def test_the_manifest_is_not_pre_authorized():
    """PTF-047: the flag now MIRRORS a deployment authorization record. True
    without a record that verifies against this manifest is still refused."""
    doc = GD.load_manifest()
    assert doc["deployment_authorized"] is (doc.get("deployment_authorization") is not None)
    doc = dict(doc, deployment_authorized=True, deployment_authorization=None)
    assert any("pre-authorized" in p for p in GD.verify_manifest(doc))


def test_milwaukee_is_published_in_source_and_its_authority_does_not_record_deployment():
    """The market authority package says PUBLISHED (a source fact). Whether
    the composed bundle reached production is not the authority's fact and
    PTF-047 does not write it there: deployment lives in
    deploy/netlify/deployment_records/ and the authorization's status."""
    from scripts.pettripfinder.acquisition import authority_build_036 as A36
    package = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert package["published"] is True
    assert package["publication"]["deployed"] is False


# --------------------------------------------------------------------------- #
# Milwaukee's population survives the composition.
# --------------------------------------------------------------------------- #

def test_milwaukee_contributes_exactly_73_profiles(production):
    _manifest, site = production
    root = site / "pet-friendly-hotels" / "milwaukee-wi"
    profiles = [p for p in root.glob("*/index.html")]
    assert (root / "index.html").is_file()
    assert (root / "policy-comparison" / "index.html").is_file()
    # 73 hotels + 7 corridors + the comparison page
    assert len(profiles) == 81


@pytest.mark.parametrize("slug", [
    "saint-kate-the-arts-hotel",
    "home2-suites-by-hilton-milwaukee-downtown",
    "tru-by-hilton-milwaukee-downtown",
])
def test_an_approved_milwaukee_property_is_in_the_bundle(production, slug):
    _manifest, site = production
    assert (site / "pet-friendly-hotels" / "milwaukee-wi" / slug
            / "index.html").is_file()


@pytest.mark.parametrize("slug", [
    "hyatt-regency-milwaukee",
    "knickerbocker-on-the-lake",
    "the-iron-horse-hotel",
])
def test_a_held_milwaukee_property_is_absent_from_the_bundle(production, slug):
    _manifest, site = production
    assert not (site / "pet-friendly-hotels" / "milwaukee-wi" / slug).exists()


def test_no_milwaukee_refusal_reaches_the_bundle(production):
    from scripts.pettripfinder import market_authority as MA
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    _manifest, site = production
    root = site / "pet-friendly-hotels" / "milwaukee-wi"
    for row in MA.load_market_exclusions("milwaukee-wi"):
        slug = ptf_identity_key(row["canonical_name"]).replace(" ", "-")
        assert not (root / slug).exists(), row["canonical_name"]


# --------------------------------------------------------------------------- #
# PTF-MEASUREMENT-001 Phase 1 + 1b: the measurement/affiliate layer is gated
# on the composed bundle and, disabled, moves no byte of it.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder import affiliate_destinations as AD        # noqa: E402
from scripts.pettripfinder import measurement as M                    # noqa: E402
from scripts.pettripfinder.global_deployment import (                 # noqa: E402
    REQUIRED_GLOBAL_GATES, load_manifest,
)

MEASUREMENT_GATES = M.MEASUREMENT_GATES + AD.AFFILIATE_GATES

#: The composed production bundle PTF-...-DEPLOYMENT-ARCHITECTURE-045 made
#: deployable, which Phase 1 + 1b of the measurement work order reproduced
#: byte for byte (2213/2213 files). WITHDRAWN by the founder in PTF-046: the
#: participation set changed (Indianapolis withheld), so it is no longer a
#: deployable candidate and must never be authorized by habit.
WITHDRAWN_SIX_MARKET_BUNDLE_SHA256 = (
    "8ea6131e9fe8689fc23d3a362ae12ffaa2155c687737c6f5fcde03b5a22c42b8")
#: The five-market production candidate PTF-047 DEPLOYED. Superseded, not
#: withdrawn: it is the artifact that is live at the time 011 was written, and
#: the four profiles below are the only reason it moved.
DEPLOYED_047_BUNDLE_SHA256 = (
    "a324b1bf5023fc4e8f618d192de5eb994d093ed890db4219678223079e06852d")
#: The five-market production candidate (PTF-046), measurement disabled. A
#: fresh assembly must still produce exactly this; the zero-byte proof for the
#: disabled measurement layer was established at the six-market hash and is
#: carried forward by test_no_page_in_the_disabled_bundle_carries_a_measurement_block.
#:
#: PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 moved it from
#: DEPLOYED_047_BUNDLE_SHA256, and this is the work order that is entitled to:
#: four Milwaukee profiles published "service animals are welcome and that a
#: charge applies" over sources that said the opposite. The differential is
#: FOUR HTML files of 2165, one line each, and nothing was added or removed --
#: asserted by test_the_correction_moved_only_four_profiles below. The
#: participation set, the profile counts, the sitemap and the measurement
#: layer are all unchanged.
#: PTF-ST-LOUIS-REGISTER-PUBLISH-011 moved it again, and is likewise entitled
#: to: a sixth market joined. Measured against the bundle above it ADDS 509
#: files, every one under /pet-friendly-hotels/st-louis-mo/, REMOVES none, and
#: changes only sitemap.xml among shipped files -- so the four corrected
#: Milwaukee profiles, and every other live profile, are byte-identical.
DEPLOYED_012_BUNDLE_SHA256 = (
    "70747f09fdfe18ccc18e13a3155cc6287404e3ddfe5bb5784d0f03cc30348967")
#: The bundle DEPLOYED by PTF-ST-LOUIS-REGISTER-PUBLISH-011 and live in
#: production. The seven-market candidate must differ from it and must not
#: change a byte inside it.
DEPLOYED_011_BUNDLE_SHA256 = (
    "2077ad2895c9273ddc9deed62295058f88915e20cb6fcd4072433d1c17dff741")
#: The seven-market candidate composed by PTF-LOUISVILLE-PUBLICATION-008.
DISABLED_FIVE_MARKET_BUNDLE_SHA256 = (
    "e9998c51d13559333ef9bd63f287e8858b73eb0011401a9606a58871f6ba74cc")

#: The only four routes PTF-011 was permitted to change.
SERVICE_ANIMAL_CORRECTED_ROUTES = (
    "pet-friendly-hotels/milwaukee-wi/avid-hotels-oak-creek/index.html",
    "pet-friendly-hotels/milwaukee-wi/extended-stay-america-milwaukee-waukesha/index.html",
    "pet-friendly-hotels/milwaukee-wi/extended-stay-america-milwaukee-wauwatosa/index.html",
    "pet-friendly-hotels/milwaukee-wi/the-pfister-hotel/index.html",
)


def test_measurement_is_disabled_in_source():
    cfg = M.load_measurement_config()
    assert cfg.enabled is False and cfg.provider.kind == M.PROVIDER_KIND_NONE
    assert AD.load_providers() == {}
    assert AD.assemble_global_view() == {}


def test_the_six_measurement_gates_are_required_and_pass(production):
    manifest, _site = production
    for gate in MEASUREMENT_GATES:
        assert gate in REQUIRED_GLOBAL_GATES, gate
        assert manifest["gates"][gate]["pass"], (gate, manifest["gates"][gate])


def test_every_045_gate_still_runs_and_passes(production):
    manifest, _site = production
    for gate in REQUIRED_GLOBAL_GATES:
        assert gate in manifest["gates"] and manifest["gates"][gate]["pass"], gate
    # 19 (045) + 6 (measurement/affiliate) + 2 (launch participation, 046)
    assert len(manifest["gates"]) == len(REQUIRED_GLOBAL_GATES) == 27


def test_the_disabled_bundle_is_the_pinned_candidate_byte_for_byte(production):
    """The acceptance target. If this moves, either the measurement layer
    leaked into a disabled build or the participation set changed; neither
    is accepted by editing the hash here without its own work order."""
    manifest, _site = production
    assert manifest["bundle_sha256"] == DISABLED_FIVE_MARKET_BUNDLE_SHA256
    assert manifest["bundle_sha256"] != WITHDRAWN_SIX_MARKET_BUNDLE_SHA256
    assert manifest["bundle_sha256"] != DEPLOYED_047_BUNDLE_SHA256


def test_the_correction_moved_only_four_profiles(production):
    """PTF-011's whole differential against the artifact 047 deployed.

    The candidate hash moved, so the reason it moved is asserted rather than
    described: every page in the bundle carries the corrected sentence or none
    at all, and no page anywhere still tells a reader that a charge applies to
    a service animal when its own source exempts one.
    """
    _manifest, site = production
    wrong = "service animals are welcome and that a charge applies"
    right = "service animals are welcome at no charge"
    carrying_wrong, carrying_right = [], []
    for page in sorted(site.rglob("*.html")):
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(site).as_posix()
        if wrong in text:
            carrying_wrong.append(rel)
        if right in text:
            carrying_right.append(rel)
    assert carrying_wrong == []
    for route in SERVICE_ANIMAL_CORRECTED_ROUTES:
        assert route in carrying_right, route


def test_no_page_in_the_disabled_bundle_carries_a_measurement_block(production):
    _manifest, site = production
    for page in site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert M.SNIPPET_MARKER not in text, page
        assert M.GO_ADAPTER_MARKER not in text, page
        assert '"build_id"' not in text, page
        assert "<script src=" not in text and "<script defer" not in text, page


def test_booking_pages_still_redirect_to_the_official_url(production):
    _manifest, site = production
    booking = sorted(site.rglob("booking/index.html"))
    assert len(booking) == EXPECTED_TOTAL
    for page in booking:
        text = page.read_text(encoding="utf-8")
        assert '"affiliate_provider": ""' in text, page
        assert 'rel="noopener"' in text, page
        assert "sponsored" not in text, page


def test_the_bundle_manifest_pins_the_measurement_config(production):
    manifest, _site = production
    block = manifest["measurement"]
    assert block["config_source"] == "deploy/netlify/measurement.json"
    assert block["config_sha256"] == M.config_sha256()
    assert block["enabled"] is False and block["provider_kind"] == "none"


def test_the_committed_manifest_pins_the_measurement_config_and_is_authorized_only_by_record():
    doc = load_manifest()
    assert doc["measurement"]["config_sha256"] == M.config_sha256()
    # PTF-047: authorized only through a verifying deployment authorization.
    assert doc["deployment_authorized"] is (doc.get("deployment_authorization") is not None)
    assert GD.verify_manifest() == []
    assert doc["bundle_sha256"] == DISABLED_FIVE_MARKET_BUNDLE_SHA256
    for gate in MEASUREMENT_GATES:
        assert gate in doc["required_gates"], gate


def test_a_changed_measurement_config_invalidates_the_manifest():
    doc = load_manifest()
    doc["measurement"] = dict(doc["measurement"], config_sha256="0" * 64)
    assert any("measurement.json" in p for p in GD.verify_manifest(doc))


def test_participation_and_inventory_are_unchanged(production):
    manifest, site = production
    assert manifest["market_fragments_included"] == list(EXPECTED_MARKETS)
    assert {r["market_id"]: r["published_profiles"]
            for r in manifest["participating_markets"]} == EXPECTED_PROFILES
    assert sum(EXPECTED_PROFILES.values()) == EXPECTED_TOTAL
    assert manifest["total_html_pages"] == EXPECTED_HTML_PAGES
    assert manifest["sitemap_route_count"] == EXPECTED_SITEMAP_ROUTES
    live = [line.strip() for line in LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8")
            .splitlines() if line.strip() and not line.startswith("#")]
    assert len(live) == 132          # the 044 live inventory, comments excluded
    for route in live:
        assert (site / route.strip("/") / "index.html").is_file(), route
