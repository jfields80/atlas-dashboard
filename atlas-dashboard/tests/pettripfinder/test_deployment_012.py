"""PTF-MILWAUKEE-SERVICE-ANIMAL-REAUTHORIZE-012 -- the production deployment.

047 built the authorization layer and deployed the first multi-market bundle.
This is the second production write, and the first one that CORRECTS something
already live. These assert the chain that made it legitimate: an authorization
that binds the corrected artifact and nothing else, a manifest that mirrors
it, a record written after the outcome, and a 047 authorization that is
history rather than a reusable key.

No build here: the artifact was verified before deployment and the record
holds what the live checks found.
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
from scripts.pettripfinder import service_animal_reattestation_012 as R12

AUTH_ID = "ptf-auth-012-70747f09fdfe"
RECORD_ID = "ptf-deploy-012-6a8c6de6fa99ff1f7bd5c7f5"
BUNDLE = "70747f09fdfe18ccc18e13a3155cc6287404e3ddfe5bb5784d0f03cc30348967"
DEPLOY_ID = "6a8c6de6fa99ff1f7bd5c7f5"
ROLLBACK = "6a8a2dada6e73cb0d819c9d0"

#: The artifact PTF-047 deployed, which this one replaced.
SUPERSEDED_BUNDLE = \
    "a324b1bf5023fc4e8f618d192de5eb994d093ed890db4219678223079e06852d"
SUPERSEDED_AUTH = "ptf-auth-047-a324b1bf5023"

FIVE = ["cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
        "milwaukee-wi", "pittsburgh-pa"]
PROFILES = {"cleveland-akron-canton-oh": 99, "columbus-oh": 88,
            "dayton-oh": 47, "milwaukee-wi": 73, "pittsburgh-pa": 26}

CORRECTED_ROUTES = [
    "pet-friendly-hotels/milwaukee-wi/avid-hotels-oak-creek/index.html",
    "pet-friendly-hotels/milwaukee-wi/extended-stay-america-milwaukee-waukesha/index.html",
    "pet-friendly-hotels/milwaukee-wi/extended-stay-america-milwaukee-wauwatosa/index.html",
    "pet-friendly-hotels/milwaukee-wi/the-pfister-hotel/index.html",
]


@pytest.fixture()
def auth():
    return copy.deepcopy(DA.load_authorization(AUTH_ID))


@pytest.fixture()
def record():
    return copy.deepcopy(
        json.loads(DA.record_path(RECORD_ID).read_text(encoding="utf-8")))


@pytest.fixture()
def manifest():
    return copy.deepcopy(GD.load_manifest())


# --------------------------------------------------------------------------- #
# The authorization.
# --------------------------------------------------------------------------- #

def test_the_authorization_is_the_012_artifact(auth):
    assert auth["schema"] == DA.AUTHORIZATION_SCHEMA
    assert auth["authorized_by"] == "founder"
    assert auth["work_order"] == R12.WORK_ORDER
    assert auth["bundle_sha256"] == BUNDLE != SUPERSEDED_BUNDLE
    assert auth["binding_identity"] == "bundle_sha256"
    assert auth["production_context"] == "production"
    assert auth["participating_markets"] == FIVE
    assert auth["profile_counts"] == PROFILES
    assert auth["total_profiles"] == 333
    assert auth["total_html_pages"] == 2147 and auth["total_files"] == 2165
    assert auth["sitemap_route_count"] == 416
    assert auth["global_gate_count"] == 27
    assert auth["measurement"] == {"enabled": False, "provider_kind": "none"}
    assert auth["affiliate"] == {"providers_enrolled": 0,
                                 "destinations_active": 0}
    assert auth["rollback_target"] == ROLLBACK
    assert auth["target_site"] == "pettripfinder-prod"
    assert auth["target_domain"] == "https://pettripfinder.com"


def test_the_authorization_is_a_new_one_and_not_a_reused_047(auth):
    assert auth["authorization_id"] == AUTH_ID != SUPERSEDED_AUTH
    superseded = DA.load_authorization(SUPERSEDED_AUTH)
    assert superseded["bundle_sha256"] == SUPERSEDED_BUNDLE
    # 047 is DEPLOYED history. It is not superseded, not reopened, not reused.
    assert superseded["authorization_status"] == DA.DEPLOYED
    assert DA.deployability_problems(superseded), \
        "a consumed authorization must never be deployable again"


def test_the_authorization_binds_the_artifact_it_deployed_and_no_other(auth):
    """It bound ONE exact artifact, and a later work order built a different one.

    PTF-ST-LOUIS-REGISTER-PUBLISH-011 registered a sixth market. That changes
    the bundle, the participation record, the profile counts and one release
    contract -- so this authorization must now REFUSE, and refuse specifically,
    naming each binding that moved. A one-byte change anywhere is a different
    artifact and needs a new authorization; that is the whole contract.
    """
    problems = DA.verify_authorization(auth)
    assert problems, "an authorization that binds a superseded artifact must refuse"
    assert any("bundle_sha256" in p for p in problems)
    assert auth["bundle_sha256"] == BUNDLE
    # Everything the deployment record says it deployed is still exactly what
    # this document says, because the document was not edited -- only the world
    # moved past it.
    assert auth["total_profiles"] == 333
    assert auth["participating_markets"] == list(FIVE)
    assert auth["headers_sha256"] == DA._sha256_file(REPO / auth["headers_source"])
    assert auth["redirects_sha256"] == DA._sha256_file(REPO / auth["redirects_source"])


def test_the_authorization_quotes_the_founder_rather_than_summarising(auth):
    source = auth["authorization_source"]
    assert R12.WORK_ORDER in source
    assert "must NOT be reused" in source
    assert "ONLY if all prior checks pass" in source
    assert "Do not authorize any St. Louis" in source


def test_the_authorization_is_consumed(auth):
    assert auth["authorization_status"] == DA.DEPLOYED
    assert DA.deployability_problems(auth), "DEPLOYED must not deploy again"
    statuses = [entry["status"] for entry in auth["status_history"]]
    assert statuses == [DA.PREPARED, DA.AUTHORIZED, DA.DEPLOYED]


def test_no_credential_in_the_authorization(auth):
    blob = json.dumps(auth).lower()
    for needle in ("nfp_", "netlify_auth_token", "site_id", "bearer "):
        assert needle not in blob


# --------------------------------------------------------------------------- #
# The manifest mirrors it.
# --------------------------------------------------------------------------- #

def test_the_manifest_now_mirrors_a_later_authorization(manifest):
    """The flag is a MIRROR of a record, never a decision. 012's record is
    consumed, so the manifest names the one that may still be deployed."""
    assert manifest["deployment_authorized"] is True
    ref = manifest["deployment_authorization"]
    assert ref["authorization_id"] != AUTH_ID
    assert ref["bundle_sha256"] == manifest["bundle_sha256"] != BUNDLE
    assert GD.verify_manifest() == []


def test_the_deployment_record_still_describes_what_went_live(manifest):
    """The manifest moved on; the record of what was deployed did not."""
    record = json.loads((REPO / "deploy" / "netlify" / "deployment_records"
                         / ("%s.json" % RECORD_ID)).read_text(encoding="utf-8"))
    assert record["bundle_sha256"] == BUNDLE
    assert record["total_profiles"] == 333
    assert record["participating_markets"] == list(FIVE)
    assert "st-louis-mo" not in record["participating_markets"]


def test_measurement_and_affiliates_were_not_switched_on(manifest, auth):
    assert manifest["measurement"]["enabled"] is False
    assert manifest["measurement"]["provider_kind"] == "none"
    assert auth["measurement"] == {"enabled": False, "provider_kind": "none"}
    assert auth["affiliate"]["providers_enrolled"] == 0
    assert auth["affiliate"]["destinations_active"] == 0


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #

def test_the_record_verifies_against_the_authorization_it_consumed(record, auth):
    assert DA.verify_record(record, auth) == []
    assert record["authorization_id"] == AUTH_ID
    assert record["bundle_sha256"] == BUNDLE
    assert record["deployment_id"] == DEPLOY_ID
    assert record["previous_deployment_id"] == ROLLBACK
    assert record["rollback_target"] == ROLLBACK
    assert record["final_status"] == DA.DEPLOYED
    assert record["rollback_used"] is False
    assert record["exit_status"] == 0


def test_the_record_says_what_the_deploy_actually_changed(record):
    diff = record["live_verification_results"]["public_differential_vs_previous_deploy"]
    assert diff["files_total"] == 2165
    assert diff["added"] == 0 and diff["removed"] == 0
    assert diff["changed"] == 4
    assert diff["changed_files"] == CORRECTED_ROUTES
    assert diff["lines_changed_per_file"] == 1


def test_the_record_holds_the_live_verification(record):
    live = record["live_verification_results"]
    corrected = live["corrected_profiles"]
    assert corrected["checked"] == 4
    assert corrected["http_200"] == 4
    assert corrected["carry_the_corrected_sentence"] == 4
    assert corrected["still_carry_the_false_sentence"] == 0
    assert corrected["bytes_match_deployed_bundle"] == 4
    assert corrected["sentence"] == \
        "The property states that service animals are welcome at no charge."
    assert len(corrected["urls"]) == 4
    assert live["sitemap"]["loc_count"] == 416
    assert live["sitemap"]["sha256"] == record["sitemap_sha256"]
    assert live["sitemap"]["matches_manifest_pin"] is True
    assert live["homepage"]["bytes_match"] is True
    spot = live["unaffected_spot_checks"]
    for market in ("milwaukee", "columbus", "dayton"):
        assert spot[market]["status"] == 200
        assert spot[market]["bytes_match_deployed_bundle"] is True
        assert spot[market]["unchanged_since_047"] is True
    assert spot["additional_routes_mismatched"] == 0


def test_no_credential_in_the_record(record):
    blob = json.dumps(record).lower()
    for needle in ("nfp_", "netlify_auth_token", "bearer "):
        assert needle not in blob
    assert "$netlify_site_id" in record["command"].lower()


def test_the_047_record_is_untouched_history():
    prior = json.loads(
        (DA.RECORDS_DIR / "ptf-deploy-047-6a8a2dada6e73cb0d819c9d0.json")
        .read_text(encoding="utf-8"))
    assert prior["bundle_sha256"] == SUPERSEDED_BUNDLE
    assert prior["deployment_id"] == ROLLBACK
    assert prior["final_status"] == DA.DEPLOYED


def test_the_two_deployments_form_a_chain():
    records = {r["deployment_record_id"]: r for r in DA.list_records()}
    assert set(records) == {"ptf-deploy-047-6a8a2dada6e73cb0d819c9d0", RECORD_ID}
    assert records[RECORD_ID]["previous_deployment_id"] == \
        records["ptf-deploy-047-6a8a2dada6e73cb0d819c9d0"]["deployment_id"]
