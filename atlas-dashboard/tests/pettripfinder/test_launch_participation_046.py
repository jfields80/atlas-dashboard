"""PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046 -- founder launch participation.

The founder withdrew Indianapolis (8 profiles) from the first multi-market
production launch on coverage, not correctness. Before this there was no
lever for that decision except a market's own source authority, which must
not be touched to change a launch. These assert:

  * the participation record exists, is explicit for every registered
    market, and only FOUNDER_AUTHORIZED_FOR_LAUNCH admits a market;
  * Indianapolis is SOURCE-READY (every assembly condition, contract
    verifying, 8 profiles) and NOT in the composed bundle -- nothing about it
    is failed or altered;
  * the five-market candidate is derived, deterministic, clean on every
    required gate, keeps all 132 live Columbus routes and all 73 Milwaukee
    profiles, and carries no Indianapolis route or sitemap entry;
  * the committed manifest pins the record and stays unauthorized.

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
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.assemble_production_site import (
    LIVE_ROUTE_INVENTORY, assemble, market_eligibility, published_hotels,
    select_markets,
)
from scripts.pettripfinder.markets import load_markets, market_by_id

SCRATCH = Path(chr(67) + ":/t/ptf046t")

FIVE = ("cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
        "milwaukee-wi", "pittsburgh-pa")
#: PTF-ST-LOUIS-REGISTER-PUBLISH-011 admitted a sixth. 046's mechanism is
#: unchanged and is what admitted it: a registered market with no participation
#: row fails the build, and only FOUNDER_AUTHORIZED_FOR_LAUNCH lets one in.
#: PTF-LOUISVILLE-PUBLICATION-008 admitted a seventh by the same mechanism,
#: and registration and the participation row were written in one step so the
#: market never existed in the state 046 forbids.
LIVE = tuple(sorted(FIVE + ("st-louis-mo", "louisville-ky")))
PROFILES = {"cleveland-akron-canton-oh": 99, "columbus-oh": 88,
            "dayton-oh": 47, "milwaukee-wi": 73, "pittsburgh-pa": 26,
            "st-louis-mo": 82, "louisville-ky": 46}
WITHHELD = "indianapolis-in"
NOT_READY = ("cincinnati-oh", "detroit-ann-arbor-mi")

#: The five-market production candidate, reproduced twice in the work order
#: and DEPLOYED by PTF-047. Superseded by
#: PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011, which corrected a false
#: service-animal statement on four Milwaukee profiles: same five markets,
#: same 333 profiles, same 416 sitemap routes, four HTML files different.
DEPLOYED_047_BUNDLE_SHA256 = (
    "a324b1bf5023fc4e8f618d192de5eb994d093ed890db4219678223079e06852d")
#: The bundle LIVE in production before St. Louis joined. Kept named: the
#: six-market candidate must ADD to it and change nothing in it.
DEPLOYED_012_BUNDLE_SHA256 = (
    "70747f09fdfe18ccc18e13a3155cc6287404e3ddfe5bb5784d0f03cc30348967")
#: The six-market bundle DEPLOYED by PTF-ST-LOUIS-REGISTER-PUBLISH-011, live in
#: production. The seven-market candidate must ADD to it and change nothing in
#: it, which is why it is kept named rather than replaced.
DEPLOYED_011_BUNDLE_SHA256 = (
    "2077ad2895c9273ddc9deed62295058f88915e20cb6fcd4072433d1c17dff741")
#: The seven-market candidate composed by PTF-LOUISVILLE-PUBLICATION-008.
EXPECTED_BUNDLE_SHA256 = (
    "38c811dfc22c185bf11a07e1c14cb7abc787c106cf7c6f119930b803bc4380df")
EXPECTED_HTML_PAGES = 2927
EXPECTED_FILES = 2945
EXPECTED_SITEMAP_ROUTES = 567
#: The withdrawn six-market candidate. Kept so nobody authorizes it by habit.
WITHDRAWN_SIX_MARKET_SHA256 = (
    "8ea6131e9fe8689fc23d3a362ae12ffaa2155c687737c6f5fcde03b5a22c42b8")


@pytest.fixture(scope="module")
def production():
    root = SCRATCH / "prod"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield assemble(output=str(root), context="production"), root / "site"
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)


def _row(market_id):
    return market_eligibility(market_by_id(load_markets(), market_id))


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #

def test_the_record_is_committed_and_names_its_decision():
    doc = LP.load_participation()
    assert doc["schema"] == LP.PARTICIPATION_SCHEMA
    decision = doc["decision"]
    assert decision["decided_by"] == "founder"
    assert "Indianapolis" in decision["reason"]
    # The current decision is 011's; 046's is preserved as what it
    # supersedes, so the lineage of a launch set stays readable from the
    # record itself.
    assert decision["work_order"] == "PTF-ST-LOUIS-REGISTER-PUBLISH-011"
    assert decision["supersedes"]["work_order"] == \
        "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046"
    assert decision["supersedes"]["founder_authorized"] == list(FIVE)


def test_every_registered_market_has_an_explicit_status():
    registered = [m.market_id for m in load_markets()]
    checks = LP.verify_participation(
        registered, {mid: _row(mid)["assemblable"] for mid in registered})
    assert checks == {"unlisted": [], "unregistered": [],
                      "source_disagreement": []}


def test_only_the_live_set_is_founder_authorized():
    assert LP.authorized_market_ids() == sorted(LIVE)
    assert LP.launch_status(WITHHELD) == \
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    for mid in NOT_READY:
        assert LP.launch_status(mid) == LP.NOT_SOURCE_READY


def test_an_unlisted_market_reads_as_never_authorized():
    """St. Louis WAS this example until it was registered and listed. The rule
    is about the record, not about any market: an id with no row is not
    authorized, and cannot become authorized by being absent."""
    assert LP.launch_status("no-such-market-xx") == LP.UNLISTED
    assert LP.is_founder_authorized("no-such-market-xx") is False


def test_an_unlisted_registered_market_is_reported_not_ignored():
    doc = LP.load_participation()
    trimmed = dict(doc, markets=[r for r in doc["markets"]
                                 if r["market_id"] != "dayton-oh"])
    checks = LP.verify_participation(
        ["dayton-oh", "columbus-oh"], {"dayton-oh": True, "columbus-oh": True},
        trimmed)
    assert checks["unlisted"] == ["dayton-oh"]


def test_a_status_that_contradicts_the_source_is_reported():
    doc = LP.load_participation()
    lying = dict(doc, markets=[
        dict(r, launch_status=LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        if r["market_id"] == "cincinnati-oh" else r for r in doc["markets"]])
    checks = LP.verify_participation(
        ["cincinnati-oh"], {"cincinnati-oh": False}, lying)
    assert checks["source_disagreement"] and \
        "cincinnati-oh" in checks["source_disagreement"][0]


def test_a_malformed_record_fails_closed(tmp_path):
    bad = tmp_path / "launch_participation.json"
    bad.write_text(json.dumps({"schema": LP.PARTICIPATION_SCHEMA,
                               "markets": [{"market_id": "columbus-oh",
                                            "launch_status": "YES"}]}),
                   encoding="utf-8")
    with pytest.raises(LP.LaunchParticipationError):
        LP.load_participation(bad)
    with pytest.raises(LP.LaunchParticipationError):
        LP.load_participation(tmp_path / "absent.json")


def test_a_record_without_a_decision_is_refused(tmp_path):
    doc = LP.load_participation()
    bad = tmp_path / "launch_participation.json"
    bad.write_text(json.dumps(dict(doc, decision={})), encoding="utf-8")
    with pytest.raises(LP.LaunchParticipationError) as caught:
        LP.load_participation(bad)
    assert "decision" in str(caught.value)


# --------------------------------------------------------------------------- #
# Indianapolis: source untouched, not selected.
# --------------------------------------------------------------------------- #

def test_indianapolis_is_source_ready_in_every_condition():
    row = _row(WITHHELD)
    assert all(row["conditions"].values()), row["conditions"]
    assert row["assemblable"] is True
    assert row["published_count"] == 8
    assert row["inventory_error"] == ""


def test_indianapolis_release_contract_still_verifies():
    assert WITHHELD in set(RC.available_market_ids())
    assert list(RC.verify_contract(WITHHELD)) == []


def test_indianapolis_is_withheld_not_failed():
    row = _row(WITHHELD)
    assert row["launch_status"] == \
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    assert row["founder_authorized_for_launch"] is False
    assert row["participates"] is False


def test_indianapolis_is_not_selected():
    chosen, rows = select_markets()
    assert [m.market_id for m in chosen] == list(LIVE)
    assert WITHHELD in [r["market_id"] for r in rows]


def test_a_founder_authorization_cannot_admit_a_market_that_is_not_source_ready():
    """Participation is source-ready AND authorized: the record is a veto
    over readiness, never a substitute for it."""
    for mid in NOT_READY:
        row = _row(mid)
        assert row["assemblable"] is False
        assert row["participates"] is False


# --------------------------------------------------------------------------- #
# The five-market candidate.
# --------------------------------------------------------------------------- #

def test_the_bundle_carries_exactly_the_live_set(production):
    manifest, _site = production
    assert manifest["market_fragments_included"] == list(LIVE)
    assert {r["market_id"]: r["published_profiles"]
            for r in manifest["participating_markets"]} == PROFILES
    assert sum(PROFILES.values()) == 461


def test_the_bundle_reports_indianapolis_as_withheld(production):
    manifest, _site = production
    excluded = {r["market_id"]: r
                for r in manifest["markets_registered_but_excluded"]}
    assert set(excluded) == {WITHHELD, *NOT_READY}
    assert excluded[WITHHELD]["assemblable"] is True
    assert excluded[WITHHELD]["launch_status"] == \
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH


def test_the_bundle_pins_the_participation_record(production):
    manifest, _site = production
    pin = manifest["launch_participation"]
    assert pin["source"] == "deploy/netlify/launch_participation.json"
    assert pin["sha256"] == LP.participation_sha256()
    assert pin["founder_authorized"] == sorted(LIVE)


def test_no_indianapolis_route_or_sitemap_entry(production):
    _manifest, site = production
    assert not (site / "pet-friendly-hotels" / "indianapolis-in").exists()
    assert not (site / "go" / "indianapolis-in").exists()
    pages = [p.relative_to(site).as_posix() for p in site.rglob("*.html")]
    assert not [p for p in pages if "indianapolis" in p], pages[:5]
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "indianapolis" not in sitemap
    assert "/pet-friendly-hotels/indianapolis-in/" not in \
        (site / "index.html").read_text(encoding="utf-8")


def test_every_required_gate_ran_and_passed(production):
    manifest, _site = production
    for gate in GD.REQUIRED_GLOBAL_GATES:
        assert gate in manifest["gates"], gate
        assert manifest["gates"][gate]["pass"], (gate, manifest["gates"][gate])
    assert len(manifest["gates"]) == len(GD.REQUIRED_GLOBAL_GATES) == 27


def test_every_gate_that_ran_is_catalogued(production):
    """The catalogue exists so a gate cannot silently stop running; the
    converse holds too, or a gate can run for a year without anyone being
    obliged to keep it (headers.context_noindex_preview_only did, 045-046)."""
    manifest, _site = production
    assert sorted(manifest["gates"]) == sorted(GD.REQUIRED_GLOBAL_GATES)


def test_the_two_participation_gates_are_required():
    assert "global.launch_participation_explicit" in GD.REQUIRED_GLOBAL_GATES
    assert "global.launch_participation_agrees_with_source" in \
        GD.REQUIRED_GLOBAL_GATES


def test_columbus_live_routes_and_milwaukee_are_preserved(production):
    manifest, site = production
    live = [line.strip() for line in LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8")
            .splitlines() if line.strip() and not line.startswith("#")]
    assert len(live) == 132
    for route in live:
        assert (site / route.strip("/") / "index.html").is_file(), route
    assert len(manifest["fragments"]["milwaukee-wi"]["hotel_routes"]) == 73


def test_the_candidate_is_the_pinned_artifact(production):
    manifest, _site = production
    assert manifest["bundle_sha256"] == EXPECTED_BUNDLE_SHA256
    assert manifest["bundle_sha256"] != WITHDRAWN_SIX_MARKET_SHA256
    assert manifest["bundle_sha256"] != DEPLOYED_047_BUNDLE_SHA256
    assert manifest["bundle_sha256"] != DEPLOYED_012_BUNDLE_SHA256
    assert manifest["bundle_sha256"] != DEPLOYED_011_BUNDLE_SHA256
    assert manifest["total_html_pages"] == EXPECTED_HTML_PAGES
    assert manifest["total_files"] == EXPECTED_FILES
    assert manifest["sitemap_route_count"] == EXPECTED_SITEMAP_ROUTES
    assert manifest["deployment_authorized"] is False


# --------------------------------------------------------------------------- #
# The committed manifest.
# --------------------------------------------------------------------------- #

def test_the_committed_manifest_verifies_and_pins_the_record():
    assert GD.verify_manifest() == []
    doc = GD.load_manifest()
    assert doc["schema"] == GD.MANIFEST_SCHEMA
    assert doc["launch_participation"]["sha256"] == LP.participation_sha256()
    assert [r["market_id"] for r in doc["participating_markets"]] == list(LIVE)
    assert doc["total_published_profiles"] == 461
    assert doc["bundle_sha256"] == EXPECTED_BUNDLE_SHA256
    # PTF-047: the flag mirrors a verifying deployment authorization record.
    assert doc["deployment_authorized"] is (doc.get("deployment_authorization") is not None)
    excluded = {r["market_id"]: r for r in doc["excluded_markets"]}
    assert excluded[WITHHELD]["launch_status"] == \
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    assert excluded[WITHHELD]["why"] == ["founder_authorized_for_launch"]


def test_a_changed_record_invalidates_the_manifest():
    doc = dict(GD.load_manifest())
    doc["launch_participation"] = dict(doc["launch_participation"],
                                       sha256="0" * 64)
    assert any("launch_participation.json has changed" in p
               for p in GD.verify_manifest(doc))


def test_a_manifest_whose_set_disagrees_with_the_record_is_refused():
    doc = dict(GD.load_manifest())
    doc["participating_markets"] = [
        r for r in doc["participating_markets"] if r["market_id"] != "dayton-oh"]
    assert any("founder authorizes" in p for p in GD.verify_manifest(doc))


def test_the_withdrawn_candidate_is_not_the_committed_one():
    assert GD.load_manifest()["bundle_sha256"] != WITHDRAWN_SIX_MARKET_SHA256
