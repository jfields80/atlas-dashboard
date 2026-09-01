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
import re
import shutil
import sys
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import PROMOTED_PET_FRIENDLY

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
from pettripfinder.conftest import (
    manifest_problems_other_than_the_lapsed_pin)

SCRATCH = Path(chr(67) + ":/t/ptf046t")

FIVE = ("cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
        "milwaukee-wi", "pittsburgh-pa")
#: PTF-ST-LOUIS-REGISTER-PUBLISH-011 admitted a sixth. 046's mechanism is
#: unchanged and is what admitted it: a registered market with no participation
#: row fails the build, and only FOUNDER_AUTHORIZED_FOR_LAUNCH lets one in.
#: PTF-LOUISVILLE-PUBLICATION-008 admitted a seventh by the same mechanism,
#: and registration and the participation row were written in one step so the
#: market never existed in the state 046 forbids.
#: PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032 admitted a ninth by the same
#: mechanism, once two things that had silently blocked it were fixed: the
#: partition lookup could not reach its artifact at all, and the artifact it
#: would have reached predated every founder signature.
LIVE = tuple(sorted(FIVE + ("st-louis-mo", "louisville-ky", "indianapolis-in",
                            "grand-rapids-holland-mi")))
PROFILES = {"cleveland-akron-canton-oh": 99, "columbus-oh": 88,
            "dayton-oh": 47, "milwaukee-wi": 73, "pittsburgh-pa": 26,
            "st-louis-mo": 82, "louisville-ky": 46, "indianapolis-in": 56,
            "grand-rapids-holland-mi": 43}
#: 046 withheld Indianapolis and PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019
#: admitted it on a founder decision. Both facts are asserted below: the
#: withholding is still provable from the participation record's own
#: supersedes block, which is where a reversed decision leaves its history.
ADMITTED_AT_019 = "indianapolis-in"
ADMITTED_AT_032 = "grand-rapids-holland-mi"
WITHHELD_BY_046 = "indianapolis-in"
# grand-rapids-holland-mi joined this list in the lineage merge, when the
# assembler first ran on a branch carrying it and could not reach its final
# partition. 032 added the table entry and rebuilt the partition from the
# signed authority, so it LEFT this list and joined LIVE.
#: Registered, and excluded from the bundle. The name is historical: both were
#: NOT_SOURCE_READY when it was chosen, and they are now excluded for two
#: DIFFERENT reasons, which is the distinction the tests below draw.
NOT_READY = ("cincinnati-oh", "detroit-ann-arbor-mi")
#: Genuinely cannot assemble: a configured market with no policy package.
#: EMPTY as of PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030. Detroit
#: left this list the way Grand Rapids did: not by gaining data, but
#: because the assembler could finally SEE the data it already had. Its
#: partition file is named with underscores and _partition_path globbed
#: for hyphens, so final_partition_present read False and the market was
#: not assemblable -- while its own bundle assembled with every gate
#: passing. No market currently demonstrates this state, and the loops
#: below iterate the tuple rather than naming a market, so they simply
#: assert nothing until one does.
NOT_ASSEMBLABLE = ()
#: Assembles cleanly and is still not admitted, because no founder authorized
#: it. PTF-CINCINNATI-HARDENED-SYNC-002 replayed Cincinnati stranded Capture
#: Pass 1 authority -- 21 profiles, 6 refusals, a contract that verifies -- and
#: corrected the row source-readiness observation from NOT_SOURCE_READY, which
#: had become false, to SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH.
#: That is a statement about the source, not an admission: the authorized set
#: did not move.
#: Detroit joins at PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030 for
#: precisely Cincinnati's reason: its row said NOT_SOURCE_READY, which had
#: become false -- 121 profiles, 81 refusals, a contract that verifies and
#: a bundle with zero broken links. Correcting the observation moved no
#: authorization; the authorized set is unchanged.
SOURCE_READY_UNAUTHORIZED = ("cincinnati-oh", "detroit-ann-arbor-mi")

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
#: The seven-market bundle DEPLOYED by PTF-LOUISVILLE-PUBLICATION-008, live
#: in production. Kept named on the same rule as the two above: the
#: eight-market candidate must ADD to it and change nothing in it.
DEPLOYED_008_BUNDLE_SHA256 = (
    "38c811dfc22c185bf11a07e1c14cb7abc787c106cf7c6f119930b803bc4380df")
#: The eight-market bundle, composed by
#: PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019 and DEPLOYED by
#: PTF-INDIANAPOLIS-DEPLOY-AUTHORIZATION-020
#: and live in production. Kept named on the same rule as the ones above: the
#: nine-market candidate must ADD to it and change nothing in it.
DEPLOYED_020_BUNDLE_SHA256 = (
    "e9998c51d13559333ef9bd63f287e8858b73eb0011401a9606a58871f6ba74cc")
#: The nine-market candidate composed by
#: PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032. NOT deployed and NOT authorised.
EXPECTED_BUNDLE_SHA256 = (
    "5fc4ae2c555d83a9986d3d071df1013cc1a9f2fcff5d509d26c49278c84defb6")
EXPECTED_HTML_PAGES = 3503
EXPECTED_FILES = 3521
EXPECTED_SITEMAP_ROUTES = 688
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
    # supersedes names the IMMEDIATE predecessor, and the flat lineage list
    # carries every ancestor with its sha256. Both are needed: an authorization
    # signed two reissues back can only be matched through the lineage, which
    # is what that block's own what_this_is says it is for.
    assert decision["work_order"] == "PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032"
    assert decision["supersedes"]["work_order"] ==         "PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019"
    # The set 032 inherited: the eight that were live before Grand Rapids.
    assert decision["supersedes"]["founder_authorized"] ==         sorted(set(LIVE) - {ADMITTED_AT_032})

    records = decision["lineage"]["records"]
    # 046 is still the oldest ancestor and its withholding is still walkable
    # from here, which is the whole point of keeping the chain in the record.
    assert records[0]["work_order"] ==         "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046"
    assert WITHHELD_BY_046 not in records[0]["founder_authorized"]
    # Each ancestor is pinned, and the newest is the one supersedes names.
    assert all(re.fullmatch(r"[0-9a-f]{64}", r["sha256"]) for r in records)
    assert records[-1]["work_order"] == decision["supersedes"]["work_order"]
    assert records[-1]["sha256"] == decision["supersedes"]["sha256"]
    # A launch set only ever grew, and every ancestor is a subset of the set
    # live today.
    seen = [set(r["founder_authorized"]) for r in records]
    assert all(a < b for a, b in zip(seen, seen[1:]))
    assert seen[-1] < set(LIVE)


def test_every_registered_market_has_an_explicit_status():
    """Every market is listed, and no row claims a readiness the source denies.

    ``source_disagreement`` caught a real one during
    PTF-CINCINNATI-HARDENED-SYNC-002: replaying Cincinnati authority made it
    assemblable while its row still read NOT_SOURCE_READY, and the assembler
    refused to build ANY bundle until the two agreed. The row was corrected to
    SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH -- the status that exists
    precisely for "passes every assembly condition; withheld from this launch by
    founder decision; nothing about the market is wrong". The authorized set did
    not move, and ``test_only_the_live_set_is_founder_authorized`` says so.
    """
    registered = [m.market_id for m in load_markets()]
    checks = LP.verify_participation(
        registered, {mid: _row(mid)["assemblable"] for mid in registered})
    assert checks == {"unlisted": [], "unregistered": [],
                      "source_disagreement": []}


def test_only_the_live_set_is_founder_authorized():
    assert LP.authorized_market_ids() == sorted(LIVE)
    assert LP.launch_status(ADMITTED_AT_019) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    for mid in NOT_ASSEMBLABLE:
        assert LP.launch_status(mid) == LP.NOT_SOURCE_READY
    for mid in SOURCE_READY_UNAUTHORIZED:
        assert LP.launch_status(mid) == (
            LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)


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
    row = _row(ADMITTED_AT_019)
    assert all(row["conditions"].values()), row["conditions"]
    assert row["assemblable"] is True
    assert row["published_count"] == PROMOTED_PET_FRIENDLY
    assert row["inventory_error"] == ""


def test_indianapolis_release_contract_still_verifies():
    assert ADMITTED_AT_019 in set(RC.available_market_ids())
    assert list(RC.verify_contract(ADMITTED_AT_019)) == []


def test_046_withheld_indianapolis_and_that_history_survives():
    """The reversal does not erase the decision it reversed.

    WHERE that history lives moved as the chain grew. 019 admitted Indianapolis
    and 032 admitted Grand Rapids, so the immediate ``supersedes`` set now names
    the eight live before Grand Rapids -- Indianapolis among them. 046's
    withholding survives in the two places that outlast any number of later
    decisions: the pinned lineage list, where every record written before 019
    still excludes it, and Indianapolis's own market row.

    The lineage is asserted by CONTENT, not by position. Reaching two levels
    back by index says nothing once a fifth decision is written; "the records
    older than the one that admitted it" stays true however long the chain gets.
    """
    doc = LP.load_participation()
    records = doc["decision"]["lineage"]["records"]
    admitting = next(i for i, r in enumerate(records)
                     if WITHHELD_BY_046 in r["founder_authorized"])
    assert records[admitting]["work_order"] ==         "PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019"
    older = records[:admitting]
    assert older, "the record that admitted Indianapolis has no ancestors"
    assert older[0]["work_order"] ==         "PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046"
    assert all(WITHHELD_BY_046 not in r["founder_authorized"] for r in older)
    row = next(r for r in doc["markets"] if r["market_id"] == WITHHELD_BY_046)
    assert row["replaces"]["launch_status"] == \
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH


def test_019_admitted_indianapolis_and_it_was_never_a_failure():
    row = _row(ADMITTED_AT_019)
    assert row["launch_status"] == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    assert row["founder_authorized_for_launch"] is True
    assert row["participates"] is True
    assert row["assemblable"] is True


def test_indianapolis_is_now_selected():
    chosen, rows = select_markets()
    assert [m.market_id for m in chosen] == list(LIVE)
    assert ADMITTED_AT_019 in [m.market_id for m in chosen]
    assert ADMITTED_AT_019 in [r["market_id"] for r in rows]


def test_a_founder_authorization_cannot_admit_a_market_that_is_not_source_ready():
    """Participation is source-ready AND authorized: the record is a veto
    over readiness, never a substitute for it."""
    for mid in NOT_ASSEMBLABLE:
        row = _row(mid)
        assert row["assemblable"] is False
        assert row["participates"] is False


def test_the_record_still_vetoes_a_market_that_is_source_ready():
    """The other half of the same rule, and the half Cincinnati now tests.

    Readiness is necessary and not sufficient. Cincinnati assembles cleanly --
    21 published profiles, a contract that verifies with zero disagreements --
    and still does not participate, because no founder has authorized it. A
    market cannot let itself into a launch by passing a gate, and correcting the
    SOURCE half of its row did not touch the AUTHORIZATION half.
    """
    for mid in SOURCE_READY_UNAUTHORIZED:
        row = _row(mid)
        assert row["assemblable"] is True
        assert row["participates"] is False
        assert LP.launch_status(mid) == (
            LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)
        assert mid not in LP.authorized_market_ids()


# --------------------------------------------------------------------------- #
# The five-market candidate.
# --------------------------------------------------------------------------- #

def test_the_bundle_carries_exactly_the_live_set(production):
    manifest, _site = production
    assert manifest["market_fragments_included"] == list(LIVE)
    assert {r["market_id"]: r["published_profiles"]
            for r in manifest["participating_markets"]} == PROFILES
    assert sum(PROFILES.values()) == 560


def test_the_bundle_excludes_only_the_two_that_are_not_source_ready(production):
    """Indianapolis has left this list. Nothing else joined it."""
    manifest, _site = production
    excluded = {r["market_id"]: r
                for r in manifest["markets_registered_but_excluded"]}
    assert set(excluded) == set(NOT_READY)
    assert ADMITTED_AT_019 not in excluded
    for mid in NOT_ASSEMBLABLE:
        assert excluded[mid]["assemblable"] is False
    # Excluded for want of an authorization, not for want of readiness -- see
    # test_the_record_still_vetoes_a_market_that_is_source_ready.
    for mid in SOURCE_READY_UNAUTHORIZED:
        assert excluded[mid]["assemblable"] is True


def test_the_bundle_pins_the_participation_record(production):
    manifest, _site = production
    pin = manifest["launch_participation"]
    assert pin["source"] == "deploy/netlify/launch_participation.json"
    assert pin["sha256"] == LP.participation_sha256()
    assert pin["founder_authorized"] == sorted(LIVE)


def test_indianapolis_routes_are_present_and_correctly_counted(production):
    """The mirror of the test 046 wrote. Its shape is deliberately kept: the
    thing that had to be ABSENT is now the thing that has to be PRESENT, and in
    exactly the quantity the package states."""
    _manifest, site = production
    hub = site / "pet-friendly-hotels" / "indianapolis-in"
    assert hub.is_dir()
    package = json.loads(
        (REPO / "launch_packages" / "pettripfinder"
         / "hotel_policy_facts_indianapolis-in.json").read_text(encoding="utf-8"))
    # The route is slugify(NAME) with "&" dropped -- PTF-LOUISVILLE-008.
    # The package KEY spells "&" as "and" (AES-SEO-001), so keying off it
    # produces "days-inn-and-suites-..." for a route that is
    # "days-inn-suites-...".
    slugs = {re.sub(r"-+", "-",
                    re.sub(r"[^a-z0-9]+", "-",
                           h["name"].lower().replace("&", " "))).strip("-")
             for h in package["hotels"]}
    assert len(slugs) == PROMOTED_PET_FRIENDLY      # 56 until 014 promoted 67
    present = {d.name for d in hub.iterdir() if d.is_dir()}
    assert slugs <= present
    assert all((hub / s / "index.html").is_file() for s in slugs)
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert sitemap.count("/pet-friendly-hotels/indianapolis-in/") == 71


def test_no_held_or_refused_indianapolis_row_reached_the_bundle(production):
    """The rows 018 deliberately did not promote must not appear."""
    _manifest, site = production
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    for slug in ("extended-stay-america-indianapolis-airport-w-southern-ave",
                 "home2-suites-by-hilton/"):
        assert slug not in sitemap, slug


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

def test_the_committed_manifest_describes_the_live_deploy_and_pins_the_record():
    """THE MANIFEST STILL DESCRIBES WHAT IS DEPLOYED. Its pin no longer matches.

    PTF-GRAND-RAPIDS-INDIANAPOLIS-LINEAGE-MERGE-033 registered
    grand-rapids-holland-mi in launch_participation.json -- it had to, because a
    registered market with no row fails the assembler gate closed for EVERY
    market -- and that changed the record's sha256. A signed deployment
    authorization BINDS that sha, so ptf-auth-020 stopped verifying the moment
    the eleventh market was listed.

    That was the design working, not damage, and it is the same thing
    PTF-ST-LOUIS-FRESH-MARKET-BENCHMARK-001 recorded: registering a market
    invalidates the signed authorization, and THE NEXT DEPLOYMENT ISSUES A NEW
    ONE. That next deployment has now happened --
    PTF-GRAND-RAPIDS-DEPLOY-AUTHORIZATION-034 -- so the lapse is healed and the
    manifest pins the record as it stands.

    The lapse is therefore no longer assertable from the committed state, and
    pretending otherwise would freeze this test at a window that has closed.
    What survives is the rule the lapse demonstrated, which this asserts
    directly: the manifest describes the live deploy, and its participation pin
    matches the record it was written against.
    """
    # PTF-CINCINNATI-HARDENED-SYNC-002 lapsed the pin again by correcting Cincinnati's source-readiness row. The manifest still
    # describes the deploy it was written for; what no longer matches is the
    # record's hash, and that is the lapse itself rather than a second defect.
    assert manifest_problems_other_than_the_lapsed_pin() == []
    doc = GD.load_manifest()
    assert doc["launch_participation"]["source"] == (
        "deploy/netlify/launch_participation.json")
    assert doc["schema"] == GD.MANIFEST_SCHEMA
    # The DEPLOYED set, which is eight. LIVE is now the nine-market candidate
    # set that 032 composed and nobody has deployed; comparing the committed
    # manifest against it would ask a record of a past deployment to describe a
    # future one -- until 034 DEPLOYED it, which is where that reasoning ends.
    assert [r["market_id"] for r in doc["participating_markets"]] == sorted(LIVE)
    assert doc["total_published_profiles"] == sum(PROFILES.values())
    # 034 deployed the bundle 032 composed, so the committed manifest and a
    # fresh assembly name the same artifact again.
    assert doc["bundle_sha256"] == EXPECTED_BUNDLE_SHA256
    assert doc["bundle_sha256"] != DEPLOYED_020_BUNDLE_SHA256
    # PTF-047: the flag mirrors a verifying deployment authorization record.
    assert doc["deployment_authorized"] is (doc.get("deployment_authorization") is not None)
    excluded = {r["market_id"]: r for r in doc["excluded_markets"]}
    assert ADMITTED_AT_019 not in excluded
    # The manifest records the deploy AS IT WAS. grand-rapids-holland-mi did
    # not exist on this branch when it was written, so its excluded set is the
    # two that were not source-ready then -- not today's NOT_READY, which has
    # since gained a third. A record of a past deploy does not learn.
    assert set(excluded) == {"cincinnati-oh", "detroit-ann-arbor-mi"}


def test_a_changed_record_invalidates_the_manifest():
    doc = dict(GD.load_manifest())
    doc["launch_participation"] = dict(doc["launch_participation"],
                                       sha256="0" * 64)
    assert any("launch_participation.json has changed" in p
               for p in GD.verify_manifest(doc))


def test_a_manifest_whose_set_disagrees_with_the_record_is_refused():
    """Dropping an authorized market must be refused for THAT reason.

    Since 033 the record also carries a lapsed pin, so this filters to the
    disagreement it is actually testing rather than accepting any complaint.
    """
    doc = dict(GD.load_manifest())
    doc["participating_markets"] = [
        r for r in doc["participating_markets"] if r["market_id"] != "dayton-oh"]
    problems = GD.verify_manifest(doc)
    # WHICH check catches it changed, and the invariant did not. "founder
    # authorizes" is raised in a branch reached only when the participation pin
    # still matches, and since 033 registered the eleventh market it does not.
    # The drop is still refused -- by the authorization, which binds the exact
    # participating set -- so this asserts the REFUSAL and that it names the
    # market removed, rather than one message's wording.
    assert any("dayton-oh" in p for p in problems), problems
    assert len(problems) > len(GD.verify_manifest()), (
        "dropping an authorized market must add a complaint of its own")


def test_the_withdrawn_candidate_is_not_the_committed_one():
    assert GD.load_manifest()["bundle_sha256"] != WITHDRAWN_SIX_MARKET_SHA256
