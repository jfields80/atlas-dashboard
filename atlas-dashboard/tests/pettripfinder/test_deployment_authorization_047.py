"""PTF-FIRST-MULTI-MARKET-AUTHORIZATION-AND-DEPLOYMENT-047 -- the authorization layer.

046 found the last gap: ``deployment_authorized`` was a boolean nobody could
legitimately flip, and nothing durable bound the founder's decision to an
exact artifact. These assert that the authorization contract binds every
pinned input of the verified manifest, refuses every way one of them can
change, is single-use, and that the exact 047 artifact passes.

No build here: the authorization authorizes the already-verified artifact and
recomputes no policy truth, so these run against the committed manifest and
the committed authorization record.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP

AUTH_ID = "ptf-auth-047-a324b1bf5023"
BUNDLE = "a324b1bf5023fc4e8f618d192de5eb994d093ed890db4219678223079e06852d"
WITHDRAWN = "8ea6131e9fe8689fc23d3a362ae12ffaa2155c687737c6f5fcde03b5a22c42b8"
FIVE = ["cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
        "milwaukee-wi", "pittsburgh-pa"]
ROLLBACK = "6a78dc1cdad05ac32bc58cec"
LIVE_SITE = {"name": "pettripfinder-prod", "ssl_url": "https://pettripfinder.com",
             "url": "https://pettripfinder.com",
             "published_deploy": {"id": ROLLBACK}}


@pytest.fixture()
def auth():
    return copy.deepcopy(DA.load_authorization(AUTH_ID))


@pytest.fixture()
def manifest():
    return copy.deepcopy(GD.load_manifest())


def _authorization_reference():
    """The block a manifest carries when it mirrors the 047 authorization."""
    return {"path": ("deploy/netlify/deployment_authorizations/%s.json"
                     % AUTH_ID),
            "authorization_id": AUTH_ID,
            "bundle_sha256": BUNDLE}


def _refuses(auth, manifest=None, needle=None):
    problems = DA.verify_authorization(auth, manifest)
    assert problems, "expected a refusal"
    if needle:
        assert any(needle in p for p in problems), problems
    return problems


# --------------------------------------------------------------------------- #
# The exact 047 artifact passes.
# --------------------------------------------------------------------------- #

def test_the_committed_authorization_is_the_047_artifact(auth):
    assert auth["schema"] == DA.AUTHORIZATION_SCHEMA
    assert auth["authorized_by"] == "founder"
    assert auth["work_order"] == \
        "PTF-FIRST-MULTI-MARKET-AUTHORIZATION-AND-DEPLOYMENT-047"
    assert auth["source_commit"].startswith("1d8d87c")
    assert auth["manifest_source_commit"].startswith("4342865")
    assert auth["bundle_sha256"] == BUNDLE
    assert auth["production_context"] == "production"
    assert auth["participating_markets"] == FIVE
    assert auth["profile_counts"] == {"cleveland-akron-canton-oh": 99,
                                      "columbus-oh": 88, "dayton-oh": 47,
                                      "milwaukee-wi": 73, "pittsburgh-pa": 26}
    assert auth["total_profiles"] == 333
    assert auth["sitemap_route_count"] == 416
    assert auth["total_html_pages"] == 2147 and auth["total_files"] == 2165
    assert auth["global_gate_count"] == 27
    assert auth["measurement"] == {"enabled": False, "provider_kind": "none"}
    assert auth["affiliate"] == {"providers_enrolled": 0, "destinations_active": 0}
    assert auth["rollback_target"] == ROLLBACK
    assert auth["target_site"] == "pettripfinder-prod"
    assert auth["target_domain"] == "https://pettripfinder.com"
    assert "indianapolis-in" not in auth["participating_markets"]


# --------------------------------------------------------------------------- #
# 047 is spent. The tree has moved on, and the gate says so.
#
# PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 corrected a false service-animal
# statement on four LIVE Milwaukee profiles. That changed Milwaukee's release
# contract and the composed bundle, so the artifact in the tree is no longer
# the artifact the founder authorized -- which the authorization document says
# in its own words: "Any different artifact requires a new authorization."
#
# These three tests used to assert that the authorization still bound the
# tree. That can only be true until the first content correction, so asserting
# it forever would mean the repository could never fix a published mistake
# without a red suite. What must hold forever is the RULE: 047 authorizes the
# artifact it names and refuses anything else, and no manifest may claim
# authorization it does not have.
# --------------------------------------------------------------------------- #

def test_the_authorization_still_binds_the_artifact_it_named(auth):
    """047 verifies against the manifest 047 was written for, not today's."""
    deployed = json.loads(
        (REPO / "deploy" / "netlify" / "deployment_records"
         / "ptf-deploy-047-6a8a2dada6e73cb0d819c9d0.json").read_text(
             encoding="utf-8"))
    assert deployed["authorization_id"] == AUTH_ID
    assert deployed["bundle_sha256"] == auth["bundle_sha256"] == BUNDLE
    assert deployed["rollback_target"] == ROLLBACK


def test_the_authorization_refuses_the_corrected_artifact(auth):
    """The corrected bundle is a DIFFERENT artifact and must not pass 047."""
    problems = DA.verify_authorization(auth)
    assert problems, "047 must refuse an artifact it does not name"
    assert any("bundle_sha256" in p or "release_contracts[milwaukee-wi]" in p
               for p in problems), problems


def test_the_authorization_document_says_a_different_artifact_needs_a_new_one(auth):
    assert "Any different artifact requires a new authorization." in \
        auth["authorization_source"]


def test_the_manifest_no_longer_points_at_this_authorization(manifest):
    """A manifest may only claim authorization it can point at, and the one it
    points at is no longer 047: PTF-...-REAUTHORIZE-012 authorized the
    corrected artifact under its own record."""
    assert manifest["bundle_sha256"] != BUNDLE
    assert manifest["deployment_authorized"] is \
        (manifest.get("deployment_authorization") is not None)
    ref = manifest.get("deployment_authorization") or {}
    assert ref.get("authorization_id") != AUTH_ID
    assert ref.get("bundle_sha256") == manifest["bundle_sha256"] != BUNDLE
    assert GD.verify_manifest() == []


#: What each later work order moved out from under this authorization. Named
#: rather than skipped wholesale, so the refusal stays SPECIFIC: an
#: authorization that stopped binding everything would prove nothing.
MOVED_BY_LATER_WORK = {
    # PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011/012 corrected four Milwaukee
    # profiles and restamped that market's contract.
    "milwaukee-wi",
    # PTF-ST-LOUIS-REGISTER-PUBLISH-011 registered a sixth market, which
    # re-issued the launch participation record and installed a contract for a
    # market that did not exist when 047 was signed.
    "st-louis-mo",
}


def test_the_authorization_binds_the_hashes_it_did_not_move(auth):
    """Everything later work did not touch still binds, so the refusal is
    specific rather than a blanket "something changed"."""
    assert auth["headers_sha256"] == DA._sha256_file(REPO / auth["headers_source"])
    assert auth["redirects_sha256"] == DA._sha256_file(REPO / auth["redirects_source"])
    for row in auth["release_contracts"]:
        if row["market_id"] in MOVED_BY_LATER_WORK:
            continue
        assert row["sha256"] == DA._sha256_file(REPO / row["path"]), row


def test_the_participation_record_it_bound_is_the_one_it_named(auth):
    """The participation record was RE-ISSUED, not edited: 047's authorization
    still names the sha it signed, and the record that superseded it says so."""
    import json as _json
    assert auth["launch_participation_sha256"] != LP.participation_sha256()
    current = _json.loads(
        (REPO / auth["launch_participation_source"]).read_text(encoding="utf-8"))
    assert current["decision"]["supersedes"]["sha256"] ==         auth["launch_participation_sha256"]
    assert current["decision"]["supersedes"]["founder_authorized"] ==         auth["founder_authorized_markets"]


def test_the_live_target_check_accepts_the_authorized_site(auth):
    assert DA.verify_target(auth, LIVE_SITE) == []


def test_no_credential_in_the_authorization(auth):
    blob = json.dumps(auth).lower()
    for needle in ("nfp_", "netlify_auth_token", "site_id", "bearer "):
        assert needle not in blob


# --------------------------------------------------------------------------- #
# Refusals: every bound input.
# --------------------------------------------------------------------------- #

def test_refuses_a_one_byte_bundle_hash_difference(auth):
    flipped = ("0" if BUNDLE[-1] != "0" else "1")
    auth["bundle_sha256"] = BUNDLE[:-1] + flipped
    _refuses(auth, needle="bundle_sha256")


def test_refuses_the_withdrawn_six_market_bundle(auth):
    auth["bundle_sha256"] = WITHDRAWN
    _refuses(auth, needle="bundle_sha256")


def test_refuses_a_source_commit_mismatch(auth):
    auth["manifest_source_commit"] = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    _refuses(auth, needle="manifest_source_commit")


def test_refuses_adding_indianapolis(auth):
    auth["participating_markets"] = sorted(FIVE + ["indianapolis-in"])
    auth["profile_counts"] = dict(auth["profile_counts"], **{"indianapolis-in": 8})
    auth["total_profiles"] = 341
    problems = _refuses(auth, needle="participating_markets")
    assert any("founder-authorized" in p for p in problems)


def test_refuses_removing_an_authorized_market(auth):
    auth["participating_markets"] = [m for m in FIVE if m != "dayton-oh"]
    auth["profile_counts"] = {k: v for k, v in auth["profile_counts"].items()
                              if k != "dayton-oh"}
    auth["total_profiles"] = 333 - 47
    _refuses(auth, needle="participating_markets")


def test_refuses_a_changed_profile_count(auth):
    auth["profile_counts"] = dict(auth["profile_counts"], **{"milwaukee-wi": 74})
    auth["total_profiles"] = 334
    _refuses(auth, needle="profile_counts")


def test_refuses_a_total_that_is_not_the_sum(auth):
    auth["total_profiles"] = 334
    _refuses(auth, needle="total_profiles")


def test_refuses_a_changed_sitemap_hash(auth):
    auth["sitemap_sha256"] = "f" * 64
    _refuses(auth, needle="sitemap_sha256")


def test_refuses_a_changed_headers_hash(auth):
    auth["headers_sha256"] = "f" * 64
    problems = _refuses(auth, needle="headers_sha256")
    assert any("has changed" in p or "artifact has" in p for p in problems)


def test_refuses_a_changed_redirects_hash(auth):
    auth["redirects_sha256"] = "f" * 64
    _refuses(auth, needle="redirects_sha256")


def test_refuses_a_changed_measurement_config(auth):
    auth["measurement_config_sha256"] = "f" * 64
    _refuses(auth, needle="measurement_config_sha256")


def test_refuses_an_enabled_measurement_layer(auth):
    auth["measurement"] = {"enabled": True, "provider_kind": "beacon_script"}
    _refuses(auth, needle="measurement")


def test_refuses_a_changed_launch_participation_record(auth):
    auth["launch_participation_sha256"] = "f" * 64
    _refuses(auth, needle="launch_participation_sha256")


def test_refuses_a_changed_release_contract_hash(auth):
    auth["release_contracts"][3]["sha256"] = "f" * 64
    _refuses(auth, needle="release_contracts[milwaukee-wi]")


def test_refuses_a_changed_release_contract_on_disk(auth, manifest, tmp_path):
    """A stale manifest and a stale authorization must not agree with each
    other: the contract file itself is re-hashed."""
    row = manifest["participating_markets"][0]
    row["release_contract_sha256"] = auth["release_contracts"][0]["sha256"] = "f" * 64
    _refuses(auth, manifest, needle="has changed since authorization")


def test_refuses_affiliate_state_that_is_not_the_repository(auth):
    auth["affiliate"] = {"providers_enrolled": 1, "destinations_active": 0}
    _refuses(auth, needle="affiliate.providers_enrolled")


def test_refuses_a_gate_catalogue_that_shrank(auth):
    auth["required_gates"] = auth["required_gates"][:-1]
    auth["global_gate_count"] = len(auth["required_gates"])
    _refuses(auth, needle="required_gates")


def test_refuses_a_preview_context(auth):
    auth["production_context"] = "preview"
    _refuses(auth, needle="production_context")


def test_refuses_the_wrong_netlify_site(auth):
    problems = DA.verify_target(auth, dict(LIVE_SITE, name="pettripfinder-preview"))
    assert any("target_site" in p for p in problems)


def test_refuses_the_wrong_production_domain(auth):
    auth["target_domain"] = "https://www.pettripfinder.com"
    _refuses(auth, needle="target_domain")
    problems = DA.verify_target(DA.load_authorization(AUTH_ID),
                                dict(LIVE_SITE, ssl_url="https://pettripfinder.netlify.app"))
    assert any("target_domain" in p for p in problems)


def test_refuses_to_deploy_when_production_has_moved(auth):
    moved = dict(LIVE_SITE, published_deploy={"id": "0123456789abcdef01234567"})
    problems = DA.verify_target(auth, moved)
    assert any("rollback_target" in p for p in problems)


def test_refuses_a_bundle_directory_that_is_not_the_artifact(auth, tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html></html>", encoding="utf-8")
    problems = DA.verify_bundle_directory(auth, site)
    assert any("hashes to" in p for p in problems)
    assert DA.verify_bundle_directory(auth, tmp_path / "absent")


# --------------------------------------------------------------------------- #
# State model: single use, no open-ended authorization.
# --------------------------------------------------------------------------- #

def test_the_state_model_is_closed():
    assert set(DA.STATUSES) == {"PREPARED", "AUTHORIZED", "DEPLOYED",
                                "ROLLED_BACK", "FAILED", "SUPERSEDED"}
    assert DA.DEPLOYABLE_STATUSES == ("AUTHORIZED",)
    for terminal in ("ROLLED_BACK", "FAILED", "SUPERSEDED"):
        assert DA.TRANSITIONS[terminal] == ()


def test_a_prepared_authorization_cannot_deploy(auth):
    auth["authorization_status"] = DA.PREPARED
    problems = DA.deployability_problems(auth)
    assert any("only ['AUTHORIZED'] may deploy" in p for p in problems)


def test_a_deployed_authorization_is_consumed(auth):
    if auth["authorization_status"] == DA.AUTHORIZED:
        auth = DA.transition(auth, DA.DEPLOYED, note="t")
    assert auth["authorization_status"] == DA.DEPLOYED
    problems = DA.deployability_problems(auth)
    assert any("only ['AUTHORIZED'] may deploy" in p for p in problems)
    with pytest.raises(DA.DeploymentAuthorizationError):
        DA.transition(auth, DA.AUTHORIZED)


def test_an_illegal_transition_is_refused(auth):
    auth["authorization_status"] = DA.SUPERSEDED
    with pytest.raises(DA.DeploymentAuthorizationError):
        DA.transition(auth, DA.DEPLOYED)
    with pytest.raises(DA.DeploymentAuthorizationError):
        DA.transition(dict(auth, authorization_status=DA.PREPARED), DA.DEPLOYED)


def test_a_superseded_authorization_cannot_deploy(auth, monkeypatch):
    later = copy.deepcopy(auth)
    later["authorization_id"] = "ptf-auth-later"
    later["authorized_at"] = "2999-01-01T00:00:00+00:00"
    later["authorization_status"] = DA.AUTHORIZED
    monkeypatch.setattr(DA, "list_authorizations", lambda: [auth, later])
    mine = dict(auth, authorization_status=DA.AUTHORIZED)
    problems = DA.deployability_problems(mine)
    assert any("superseded by later authorization ptf-auth-later" in p
               for p in problems)


def test_transitions_keep_history(auth):
    moved = DA.transition(dict(auth, authorization_status=DA.AUTHORIZED),
                          DA.DEPLOYED, note="n", deployment_id="x" * 24)
    assert moved["status_history"][-1]["status"] == DA.DEPLOYED
    assert moved["status_history"][-1]["deployment_id"] == "x" * 24
    assert len(moved["status_history"]) == len(auth["status_history"]) + 1


# --------------------------------------------------------------------------- #
# Manifest integration.
# --------------------------------------------------------------------------- #

def test_a_manifest_flipped_without_a_record_is_pre_authorized(manifest):
    doc = dict(manifest, deployment_authorized=True, deployment_authorization=None)
    assert any("pre-authorized" in p for p in GD.verify_manifest(doc))


def test_a_manifest_referencing_an_unknown_record_is_refused(manifest):
    doc = dict(manifest, deployment_authorized=True,
               deployment_authorization={"authorization_id": "nope",
                                         "path": "x", "bundle_sha256": BUNDLE})
    assert any("pre-authorized" in p for p in GD.verify_manifest(doc))


def test_a_manifest_whose_bundle_moved_under_its_authorization_is_refused():
    """The committed manifest claims no authorization since PTF-011, so the
    check is exercised against a manifest that DOES claim one: 047's, with the
    bundle moved out from under it."""
    doc = dict(GD.load_manifest(), bundle_sha256=WITHDRAWN,
               deployment_authorized=True,
               deployment_authorization=_authorization_reference())
    problems = GD.verify_manifest(doc)
    assert any("bundle_sha256" in p for p in problems), problems


def test_authorize_manifest_refuses_an_unbound_authorization(auth):
    auth["bundle_sha256"] = WITHDRAWN
    with pytest.raises(DA.DeploymentAuthorizationError):
        DA.authorize_manifest(auth)


# --------------------------------------------------------------------------- #
# Deployment record.
# --------------------------------------------------------------------------- #

def _record(auth, **over):
    kw = dict(deployment_record_id="ptf-deploy-test", deployment_id="a" * 24,
              previous_deployment_id=ROLLBACK, deployed_at="2026-08-22T00:00:00+00:00",
              deployer={"executed_by": "test"}, production_url="https://pettripfinder.com",
              deployed_directory="C:/t/x/site", command="netlify deploy --prod --no-build",
              global_gate_results={"pass": 27, "fail": 0},
              live_verification_results={"homepage": {"pass": True}},
              final_status=DA.DEPLOYED, rollback_used=False)
    kw.update(over)
    return DA.build_deployment_record(auth, **kw)


def test_a_deployed_record_needs_a_deployed_authorization(auth):
    rec = _record(auth)
    deployed = dict(auth, authorization_status=DA.DEPLOYED)
    assert DA.verify_record(rec, deployed) == []
    problems = DA.verify_record(rec, dict(auth, authorization_status=DA.AUTHORIZED))
    assert any("record says DEPLOYED but authorization" in p for p in problems)


def test_a_deployed_record_may_not_claim_a_rollback(auth):
    rec = _record(auth, rollback_used=True, rollback_reason="x")
    assert any("may not claim a rollback" in p
               for p in DA.verify_record(rec, dict(auth, authorization_status=DA.DEPLOYED)))


def test_a_deployed_record_with_a_failed_live_check_is_refused(auth):
    rec = _record(auth, live_verification_results={"homepage": {"pass": False}})
    assert any("failed live checks" in p
               for p in DA.verify_record(rec, dict(auth, authorization_status=DA.DEPLOYED)))


def test_a_rolled_back_record_must_restore_the_rollback_target(auth):
    rec = _record(auth, final_status=DA.ROLLED_BACK, rollback_used=True,
                  rollback_reason="homepage 500", restored_deployment_id="b" * 24)
    problems = DA.verify_record(rec, dict(auth, authorization_status=DA.ROLLED_BACK))
    assert any("must restore the rollback_target" in p for p in problems)
    ok = _record(auth, final_status=DA.ROLLED_BACK, rollback_used=True,
                 rollback_reason="homepage 500", restored_deployment_id=ROLLBACK)
    assert DA.verify_record(ok, dict(auth, authorization_status=DA.ROLLED_BACK)) == []


def test_a_record_that_disagrees_with_its_authorization_is_refused(auth):
    rec = _record(auth)
    rec["bundle_sha256"] = WITHDRAWN
    rec["total_profiles"] = 341
    problems = DA.verify_record(rec, dict(auth, authorization_status=DA.DEPLOYED))
    assert any("bundle_sha256" in p for p in problems)
    assert any("total_profiles" in p for p in problems)


def test_a_record_carrying_a_credential_is_refused(auth):
    rec = _record(auth, command="netlify deploy --auth nfp_secret")
    assert any("credential" in p
               for p in DA.verify_record(rec, dict(auth, authorization_status=DA.DEPLOYED)))


def test_write_record_refuses_inconsistency(auth, monkeypatch, tmp_path):
    monkeypatch.setattr(DA, "RECORDS_DIR", tmp_path)
    rec = _record(auth, deployment_id=ROLLBACK)   # equals previous
    with pytest.raises(DA.DeploymentAuthorizationError):
        DA.write_record(rec)
