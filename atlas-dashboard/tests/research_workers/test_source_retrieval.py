"""PTF-WORKERS-003 -- seam tests for the official-source retrieval adapter.

Scope discipline: these tests cover the SEAM only. The importer's own SSRF,
redirect, normalization and domain-pack behaviour is already covered by
tests/pettripfinder/importer/* and is exercised here as a regression, never
re-implemented. Every test is offline -- the importer's ``StaticPageFetcher``
is the fetcher, so no test in this file can reach the public internet.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import FetchResult
from services.research_workers import source_retrieval as SR
from services.research_workers import vocabulary as V


# --------------------------------------------------------------------------- #
# Test doubles.
# --------------------------------------------------------------------------- #

class MemoryCas:
    """Content-addressed store standing in for ArtifactStoreRepository."""

    def __init__(self):
        self.blobs = {}

    def put_bytes(self, data: bytes) -> str:
        import hashlib
        h = hashlib.sha256(data).hexdigest()
        self.blobs[h] = data
        return h

    def get_bytes(self, digest: str) -> bytes:
        return self.blobs[digest]


REDROOF = SR.ExpectedEntity(
    listing_key="red roof plus columbus downtown convention center",
    listing_name="Red Roof PLUS+ Columbus Downtown Convention Center",
    address="111 East Nationwide Blvd", city="Columbus", state="OH",
    postal_code="43215", phone="614-224-6539",
    website_url="https://www.redroof.com/property/oh/columbus/rri262")

REDROOF_URL = "https://www.redroof.com/property/oh/columbus/rri262"

REDROOF_HTML = """<html><head><title>Red Roof PLUS+ Columbus Downtown Convention Center</title>
<link rel="canonical" href="https://www.redroof.com/property/oh/columbus/rri262"></head>
<body><h1>Red Roof PLUS+ Columbus Downtown Convention Center</h1>
<p>111 East Nationwide Blvd, Columbus, OH 43215</p><p>Phone: 614-224-6539</p>
<h2>Pet Policy</h2>
<p>Up to two well-behaved domestic pets (cat or dog, up to 80 pounds each) are
welcome per room. There is no additional pet fee at this location.</p>
<a href="/why-red-roof/pet-policy">Pet Policy details</a>
<a href="/property/oh/columbus/rri262/amenities">Hotel Amenities</a>
<a href="/account/login">My Account</a>
<a href="https://www.facebook.com/redroof">Facebook</a>
</body></html>"""


def _run(url, html=None, expected=REDROOF, result=None, observed_at="2026-07-27"):
    fetcher = StaticPageFetcher()
    if result is not None:
        fetcher.add_result(url, result)
    else:
        fetcher.add_html(url, html)
    return SR.retrieve_official_source(
        assignment_id="test-assignment", expected=expected, source_url=url,
        fetcher=fetcher, cas=MemoryCas(), observed_at=observed_at)


# --------------------------------------------------------------------------- #
# 1. Success -> valid SourceDocument.
# --------------------------------------------------------------------------- #

def test_successful_snapshot_becomes_valid_source_document():
    out = _run(REDROOF_URL, REDROOF_HTML)
    assert out.status == SR.RETRIEVED
    assert out.ready_for_extraction is True
    doc = out.source_document
    assert doc is not None
    assert doc.source_url == REDROOF_URL
    assert doc.retrieval_status == V.RETRIEVAL_OK
    assert doc.retrieved_at == "2026-07-27"
    # the policy sentence actually survived normalization
    assert "up to 80 pounds each" in doc.content_text.lower()
    assert "two well-behaved domestic pets" in doc.content_text.lower()
    # hashes recorded for both raw bytes and normalized text
    assert len(out.raw_content_hash) == 64
    assert len(out.normalized_text_hash) == 64
    # PTF-WORKERS-005 correction. This previously asserted equality with the
    # snapshot's BARE hex digest, which is what made the document fail
    # SourceDocument.validate() with "content_hash mismatch" -- the assertion
    # was encoding the defect rather than catching it. The contract's canonical
    # form is "sha256:<hex>"; the digest itself is unchanged.
    assert doc.content_hash == "sha256:" + out.normalized_text_hash
    assert out.identity == SR.EXACT_MATCH


def test_source_document_satisfies_the_existing_contract():
    """The seam must produce a document the worker pipeline already accepts."""
    out = _run(REDROOF_URL, REDROOF_HTML)
    d = out.source_document.to_dict()
    assert set(d) == {"source_url", "source_type", "retrieved_at", "title",
                      "content_text", "content_hash", "retrieval_status"}


def test_source_document_actually_validates():
    """The regression that would have caught BOTH latent defects.

    ``validate()`` was never called on a document from this seam, so two bugs
    survived: source_type carried the importer's relationship slug
    ("EXACT_ENTITY_DOMAIN", not in the worker vocabulary), and content_hash
    carried a bare hex digest instead of the canonical "sha256:" form. Each
    alone would have raised ContractError the first time a real assignment was
    built from a retrieved page.
    """
    doc = _run(REDROOF_URL, REDROOF_HTML).source_document
    doc.validate()
    assert doc.source_type in V.SOURCE_TYPES
    assert doc.source_type == V.SOURCE_OFFICIAL_PROPERTY
    assert doc.is_usable_official is True


# --------------------------------------------------------------------------- #
# 2-7. Failure mapping. No reason slug is collapsed.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("reason,expected_status", [
    (C.REASON_UNSAFE_HOST, SR.REJECTED_UNSAFE_URL),
    (C.REASON_UNSAFE_REDIRECT, SR.REJECTED_UNSAFE_URL),
    (C.REASON_UNSAFE_URL, SR.REJECTED_UNSAFE_URL),
    (C.REASON_INVALID_SCHEME, SR.REJECTED_UNSAFE_URL),
    (C.REASON_INVALID_PORT, SR.REJECTED_UNSAFE_URL),
    (C.REASON_BLOCKED_SOURCE, SR.ACCESS_BLOCKED),
    (C.REASON_RATE_LIMITED_SOURCE, SR.ACCESS_BLOCKED),
    (C.REASON_UNSUPPORTED_CONTENT_TYPE, SR.UNSUPPORTED_CONTENT),
    (C.REASON_PDF_SOURCE, SR.UNSUPPORTED_CONTENT),
    (C.REASON_OVERSIZED_RESPONSE, SR.UNSUPPORTED_CONTENT),
    (C.REASON_FETCH_TIMEOUT, SR.NETWORK_ERROR),
    (C.REASON_DNS_RESOLUTION_FAILED, SR.NETWORK_ERROR),
    (C.REASON_REDIRECT_LIMIT, SR.NETWORK_ERROR),
    (C.REASON_FETCH_FAILED, SR.NETWORK_ERROR),
])
def test_importer_reason_maps_to_worker_status_and_is_preserved(reason, expected_status):
    url = "https://www.example-hotel.com/policy"
    out = _run(url, result=FetchResult(url, False, reason=reason))
    assert out.status == expected_status
    assert out.importer_reason == reason      # never collapsed
    assert out.source_document is None
    assert out.ready_for_extraction is False


def test_unsafe_localhost_url_is_rejected_by_the_real_fetcher_gate():
    """Regression against the importer's own SSRF gate -- not a re-test of it."""
    from scripts.pettripfinder.importer.fetch import assert_fetchable
    for bad in ("http://localhost/x", "http://127.0.0.1/x", "http://10.0.0.5/x",
                "http://169.254.1.1/x", "file:///etc/passwd", "ftp://h/x",
                "https://user:pw@example.com/x"):
        ok, reason = assert_fetchable(bad)
        assert ok is False, bad
        assert reason in SR.REASON_TO_STATUS, (bad, reason)
        assert SR.REASON_TO_STATUS[reason] == SR.REJECTED_UNSAFE_URL


def test_http_404_maps_to_not_found_not_generic_network_error():
    url = "https://www.redroof.com/property/gone"
    out = _run(url, result=FetchResult(url, False, final_url=url, http_status=404,
                                       reason=C.REASON_FETCH_FAILED))
    assert out.status == SR.NOT_FOUND


def test_javascript_shell_maps_to_render_required():
    url = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail"
    shell = ("<html><head><title>Staybridge Suites</title></head><body>"
             "<div id=\"root\"></div><script src=a.js></script>"
             "<script src=b.js></script><script src=c.js></script></body></html>")
    out = _run(url, shell, expected=SR.ExpectedEntity(
        listing_key="staybridge suites columbus dublin",
        listing_name="Staybridge Suites Columbus Dublin", city="Dublin", state="OH"))
    assert out.status == SR.RENDER_REQUIRED
    assert out.failure_reason == C.REASON_JAVASCRIPT_RENDERED
    assert out.source_document is None


# --------------------------------------------------------------------------- #
# 5. Entity identity -- the Drury Plaza case.
# --------------------------------------------------------------------------- #

DRURY_EXPECTED = SR.ExpectedEntity(
    listing_key="drury plaza hotel columbus downtown",
    listing_name="Drury Plaza Hotel Columbus Downtown",
    address="88 East Nationwide Blvd", city="Columbus", state="OH",
    phone="614-221-7008")

DRURY_OTHER_PROPERTY_HTML = """<html><head>
<title>Drury Inn &amp; Suites Columbus Convention Center</title></head><body>
<h1>Drury Inn &amp; Suites Columbus Convention Center</h1>
<p>88 E. Nationwide Blvd is not this address.</p>
<p>Address: 640 Marconi Blvd, Columbus, OH 43215</p><p>Phone: 614-221-9700</p>
<h2>Pet Policy</h2><p>Pets welcome, $50 per room per night.</p></body></html>"""


def test_entity_mismatch_fails_closed_and_yields_no_source_document():
    out = _run("https://www.druryhotels.com/locations/columbus-oh/"
               "drury-inn-and-suites-columbus-convention-center",
               DRURY_OTHER_PROPERTY_HTML, expected=DRURY_EXPECTED)
    assert out.status == SR.ENTITY_MISMATCH
    assert out.identity in (SR.MISMATCH, SR.AMBIGUOUS, SR.NOT_ENOUGH_INFORMATION)
    assert out.source_document is None, "mismatched page must not become evidence"
    assert out.ready_for_extraction is False


def test_address_only_page_without_name_is_not_promoted_to_exact():
    html = ("<html><head><title>Welcome</title></head><body>"
            "<p>111 East Nationwide Blvd, Columbus, OH</p></body></html>")
    out = _run(REDROOF_URL, html)
    assert out.identity in (SR.AMBIGUOUS, SR.STRONG_MATCH)
    if out.identity == SR.AMBIGUOUS:
        assert out.status == SR.ENTITY_MISMATCH


def test_phone_match_plus_address_match_is_strong_without_name():
    html = ("<html><head><title>Reservations</title></head><body>"
            "<p>111 East Nationwide Blvd, Columbus, OH 43215</p>"
            "<p>614-224-6539</p><p>Pets welcome.</p></body></html>")
    out = _run(REDROOF_URL, html)
    assert out.identity == SR.STRONG_MATCH
    assert out.status == SR.RETRIEVED


# --------------------------------------------------------------------------- #
# 8. Brand-policy applicability gate is preserved, not re-derived.
# --------------------------------------------------------------------------- #

HILTON_BRAND_LIST_HTML = """<html><head><title>Pet-Friendly Hotels in Dublin</title></head>
<body><h1>Pet-Friendly Hotels in Dublin, Ohio</h1>
<p>Hampton Inn Columbus Dublin is listed among our pet-friendly hotels.</p>
<p>Dublin, OH</p>
<p>Pet fees and policies vary by hotel; charges apply at participating hotels.</p>
</body></html>"""


def test_brand_page_participating_scope_is_flagged_not_applicable():
    expected = SR.ExpectedEntity(
        listing_key="hampton inn columbus dublin",
        listing_name="Hampton Inn Columbus Dublin", city="Dublin", state="OH",
        website_url="https://www.hilton.com/en/hotels/cmhnwhx-hampton-columbus-dublin/")
    out = _run("https://www.hilton.com/en/locations/usa/ohio/dublin/pet-friendly/",
               HILTON_BRAND_LIST_HTML, expected=expected)
    if out.status == SR.RETRIEVED:
        # a brand-scope page must never be silently treated as property policy
        assert out.brand_policy_scope != SR.BRAND_SCOPE_UNIVERSAL or out.policy_applicable
        if out.source_role == SR.LODGING_SOURCE_ROLE_BRAND_POLICY:
            assert out.policy_applicable is False
            assert any(w.startswith("brand_policy_scope_") for w in out.warnings)


# --------------------------------------------------------------------------- #
# PTF-WORKERS-003 defect regression: a multi-property directory page must
# never be classified as THIS property's policy source.
#
# Reproduces the live Hilton page the first pilot hit. Both URLs sit on
# hilton.com, so the importer's host-level relationship is
# EXACT_ENTITY_DOMAIN ("source_host_equals_website") -- identical to a real
# property page. The hotel's name and city both appear, because it is a Dublin
# listing that includes it. Before the fix this yielded
# PROPERTY_POLICY_SOURCE + policy_applicable=True.
# --------------------------------------------------------------------------- #

HILTON_DIRECTORY_URL = "https://www.hilton.com/en/locations/usa/ohio/dublin/pet-friendly/"

HILTON_DIRECTORY_HTML = """<html><head>
<title>Pet-Friendly Hotels in Dublin, OH - Find Hotels - Hilton</title></head><body>
<h1>Pet-Friendly Hotels in Dublin, OH</h1>
<p>Dublin, Ohio</p>
<p>Hampton Inn Columbus Dublin, 3920 Tuller Rd</p>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/doubletree-by-hilton/">DoubleTree</a>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/embassy-suites/">Embassy Suites</a>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/hampton-by-hilton/">Hampton by Hilton</a>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/hilton-garden-inn/">Hilton Garden Inn</a>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/home2-suites/">Home2 Suites</a>
<a href="/en/locations/usa/ohio/dublin/pet-friendly/homewood-suites/">Homewood Suites</a>
</body></html>"""

HAMPTON_EXPECTED = SR.ExpectedEntity(
    listing_key="hampton inn columbus dublin",
    listing_name="Hampton Inn Columbus Dublin",
    address="3920 Tuller Rd", city="Dublin", state="OH", phone="614-889-0573",
    website_url="https://www.hilton.com/en/hotels/cmhnwhx-hampton-columbus-dublin/")


def test_multi_property_directory_is_not_this_property_policy_source():
    """Regression: fails before the fix, passes after."""
    out = _run(HILTON_DIRECTORY_URL, HILTON_DIRECTORY_HTML, expected=HAMPTON_EXPECTED)
    assert out.source_role == SR.LODGING_SOURCE_ROLE_BRAND_POLICY, (
        "a page listing sibling properties must not be PROPERTY_POLICY_SOURCE")
    assert out.policy_applicable is False, (
        "brand/listing evidence must not be applied to this property unless the "
        "brand policy is universal")
    assert "directory_listing_page" in out.warnings


def test_non_applicable_evidence_is_never_ready_for_extraction():
    """Second half of the same defect: a fetched-but-inapplicable page must not
    be handed to the extractor, however clean the retrieval was."""
    out = _run(HILTON_DIRECTORY_URL, HILTON_DIRECTORY_HTML, expected=HAMPTON_EXPECTED)
    assert out.status == SR.RETRIEVED          # bytes did arrive, cleanly
    assert out.source_document is not None
    assert out.policy_applicable is False
    assert out.ready_for_extraction is False   # ...but it is NOT extractable
    assert out.to_dict()["ready_for_extraction"] is False


def test_directory_detection_uses_sibling_paths_not_host():
    """The importer still reports host-level EXACT_ENTITY_DOMAIN -- the fix must
    not depend on changing that."""
    out = _run(HILTON_DIRECTORY_URL, HILTON_DIRECTORY_HTML, expected=HAMPTON_EXPECTED)
    assert out.source_relationship == C.REL_EXACT_ENTITY_DOMAIN
    assert SR.looks_like_directory_page(out.final_url, out.policy_candidates) is True


def test_genuine_property_page_is_not_flagged_as_directory():
    """The Red Roof property page links to a policy page and an amenities page,
    but no sibling *properties* beneath its own path."""
    out = _run(REDROOF_URL, REDROOF_HTML)
    assert SR.looks_like_directory_page(out.final_url, out.policy_candidates) is False
    assert out.source_role == SR.LODGING_SOURCE_ROLE_PROPERTY_POLICY
    assert out.policy_applicable is True
    assert "directory_listing_page" not in out.warnings


def test_strong_match_alone_no_longer_grants_property_role():
    """Identity STRONG_MATCH (name in body + city) is a listing-page signature;
    only EXACT_MATCH may carry the property role."""
    html = ("<html><head><title>Reservations</title></head><body>"
            "<p>111 East Nationwide Blvd, Columbus, OH 43215</p>"
            "<p>614-224-6539</p><p>Pets welcome.</p></body></html>")
    out = _run(REDROOF_URL, html)
    assert out.identity == SR.STRONG_MATCH
    assert out.source_role == SR.LODGING_SOURCE_ROLE_BRAND_POLICY
    assert out.policy_applicable is False


# --------------------------------------------------------------------------- #
# Policy-candidate discovery: bounded, same-domain, deterministic.
# --------------------------------------------------------------------------- #

def test_policy_candidates_ranked_deterministically_and_bounded():
    out = _run(REDROOF_URL, REDROOF_HTML)
    urls = [c.url for c in out.policy_candidates]
    assert urls, "expected at least the pet-policy link"
    assert urls[0].endswith("/why-red-roof/pet-policy"), urls
    # off-domain and account/social links excluded
    assert not any("facebook" in u for u in urls)
    assert not any("/account/" in u for u in urls)
    assert all(u.startswith("https://www.redroof.com/") for u in urls)
    assert len(out.policy_candidates) <= SR.MAX_CANDIDATES
    # stable across repeated runs
    again = _run(REDROOF_URL, REDROOF_HTML)
    assert [c.url for c in again.policy_candidates] == urls


def test_duplicate_and_circular_links_are_deduplicated():
    html = ("<html><head><title>Red Roof PLUS+ Columbus Downtown Convention Center"
            "</title></head><body><p>111 East Nationwide Blvd</p><p>614-224-6539</p>"
            "<a href='/pets'>Pets</a><a href='/pets'>Pets</a>"
            "<a href='/pets#top'>Pets anchor</a>"
            "<a href='https://www.redroof.com/pets'>Pets abs</a></body></html>")
    out = _run(REDROOF_URL, html)
    urls = [c.url for c in out.policy_candidates]
    assert len(urls) == len(set(urls))
    assert urls.count("https://www.redroof.com/pets") == 1


# --------------------------------------------------------------------------- #
# Determinism + no secrets in artifacts.
# --------------------------------------------------------------------------- #

def test_artifact_is_deterministic_and_contains_no_secrets():
    a = _run(REDROOF_URL, REDROOF_HTML).to_dict()
    b = _run(REDROOF_URL, REDROOF_HTML).to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    blob = json.dumps(a).lower()
    for banned in ("authorization", "cookie", "set-cookie", "api_key", "apikey",
                   "bearer", "openai_api_key", "password", "secret"):
        assert banned not in blob, banned
    # the artifact records hashes and a byte count, never the page text itself
    assert "content_text" not in a["source_document"]      # key absent, not substring
    assert a["source_document"]["content_text_bytes"] > 0
    assert "well-behaved domestic pets" not in json.dumps(a)


def test_normalized_text_is_stable_across_runs():
    a = _run(REDROOF_URL, REDROOF_HTML)
    b = _run(REDROOF_URL, REDROOF_HTML)
    assert a.normalized_text_hash == b.normalized_text_hash
    assert a.raw_content_hash == b.raw_content_hash


# --------------------------------------------------------------------------- #
# Model separation: retrieval never calls a model or needs a credential.
# --------------------------------------------------------------------------- #

def test_retrieval_makes_zero_model_calls_and_needs_no_credential(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", raising=False)

    calls = []

    def _boom(*a, **k):                      # any provider construction is a bug
        calls.append(a)
        raise AssertionError("retrieval must not build a model provider")

    import services.research_workers.providers as P
    monkeypatch.setattr(P, "build_provider", _boom)

    out = _run(REDROOF_URL, REDROOF_HTML)
    assert out.status == SR.RETRIEVED
    assert calls == []


def test_retrieval_module_imports_no_model_provider_at_module_scope():
    import inspect
    src = inspect.getsource(SR)
    assert "build_provider" not in src
    assert "openai" not in src.lower().replace("openai_api_key", "")


# --------------------------------------------------------------------------- #
# The existing evidence_text mode must be untouched.
# --------------------------------------------------------------------------- #

def test_existing_evidence_text_assignment_builder_is_unchanged():
    """The CSV-evidence path the offline benchmarks depend on still works."""
    from services.research_workers import columbus_pilot as CP
    assert hasattr(CP, "APPROVED_MODEL_ID")
    assert CP.APPROVED_PROVIDER == "openai"
    # the seam did not remove or rename the pilot's own SourceDocument builder
    src = __import__("inspect").getsource(CP)
    assert "evidence_text" in src


# --------------------------------------------------------------------------- #
# PTF-CAPTURE-004A -- policy-level RENDER_REQUIRED, end to end.
#
# The unit rules live in test_render_evidence.py. What matters here is that the
# seam applies them in the right PLACE: last, so it can only ever reclassify an
# outcome that was about to be RETRIEVED, and never rescue a page that failed
# an earlier gate.
# --------------------------------------------------------------------------- #

LAQUINTA = SR.ExpectedEntity(
    listing_key="la quinta columbus west hilliard",
    listing_name="La Quinta Inn & Suites by Wyndham Columbus West - Hilliard",
    address="5510 Trabue Rd", city="Columbus", state="OH",
    postal_code="43228", phone="614-878-8844",
    website_url="https://www.wyndhamhotels.com/laquinta/columbus-ohio/"
                "la-quinta-columbus-west-hilliard/overview")

LAQUINTA_URL = ("https://www.wyndhamhotels.com/laquinta/columbus-ohio/"
                "la-quinta-columbus-west-hilliard/overview")

# The shape of the real page: identity and a policy LANDMARK statically, the
# policy VALUES nowhere. Padded so it is not mistaken for an empty shell.
LAQUINTA_HTML = """<html><head><title>La Quinta Inn &amp; Suites by Wyndham Columbus West - Hilliard</title>
<link rel="canonical" href="%s"></head>
<body><h1>La Quinta Inn &amp; Suites by Wyndham Columbus West - Hilliard</h1>
<p>5510 Trabue Rd, Columbus, OH 43228</p><p>Phone: 614-878-8844</p>
<div class="row policy-lists"><div class="policy-items pet-policy">
<span class="display-inline-block">Pet &amp; Service Animal Policy</span>
<span class="display-block policy-desc pet-policy-desc"></span></div></div>
<a href="#" data-target="#hotelPoliciesLightbox">Hotel Policies</a>
<p>Our pet-friendly hotel is a short drive from the mall. %s</p>
</body></html>""" % (LAQUINTA_URL, "Comfortable rooms and a warm welcome await. " * 60)

LAQUINTA_RENDERED = ("Service Animals - ADA-defined service animals are welcome "
                     "free of charge. / Dogs Allowed - 2 dogs max. 75lbs or less "
                     "per pet. / Fees - 25 USD per pet per night. Max 75 USD per "
                     "stay. / Other Information - Contact hotel for details.")


def _run_rendered(url, html, expected, rendered):
    fetcher = StaticPageFetcher()
    fetcher.add_html(url, html)
    return SR.retrieve_official_source(
        assignment_id="test-004a", expected=expected, source_url=url,
        fetcher=fetcher, cas=MemoryCas(), observed_at="2026-08-01",
        rendered_policy_text=rendered)


def test_without_rendered_evidence_the_page_stays_retrieved():
    """The default path is untouched: no rendered evidence, no reclassification.
    This is what every existing caller does."""
    out = _run(LAQUINTA_URL, LAQUINTA_HTML, expected=LAQUINTA)
    assert out.status == SR.RETRIEVED
    assert out.identity == SR.EXACT_MATCH


def test_rendered_only_policy_values_become_render_required():
    out = _run_rendered(LAQUINTA_URL, LAQUINTA_HTML, LAQUINTA, LAQUINTA_RENDERED)
    assert out.status == SR.RENDER_REQUIRED
    assert out.failure_reason == "policy_values_require_rendering"
    assert "policy_values_absent_from_static_html" in out.warnings
    # the document is still produced; this is a routing decision, not a failure
    assert out.source_document is not None
    assert out.identity == SR.EXACT_MATCH


def test_render_required_is_capture_worthy_so_gate1_now_accepts_it():
    """The whole point: this status is what lets an operator legitimately open
    the page in a browser."""
    from services.research_workers.operator_capture import CAPTURE_WORTHY

    out = _run_rendered(LAQUINTA_URL, LAQUINTA_HTML, LAQUINTA, LAQUINTA_RENDERED)
    assert out.status in CAPTURE_WORTHY


def test_a_page_serving_its_values_statically_is_unaffected():
    """Red Roof states its policy in the static HTML. Even handed rendered
    evidence, it must stay RETRIEVED -- the automated path can read it."""
    out = _run_rendered(REDROOF_URL, REDROOF_HTML, REDROOF,
                        "Up to two pets, 80 pounds each, $25 per night.")
    assert out.status == SR.RETRIEVED


def test_rendered_evidence_cannot_rescue_a_blocked_page():
    """ACCESS_BLOCKED is decided before this rule is consulted, and stays."""
    blocked = FetchResult(
        LAQUINTA_URL, False, final_url=LAQUINTA_URL, http_status=403,
        reason=C.REASON_BLOCKED_SOURCE, body=b"", content_type="text/html")
    fetcher = StaticPageFetcher()
    fetcher.add_result(LAQUINTA_URL, blocked)
    out = SR.retrieve_official_source(
        assignment_id="t", expected=LAQUINTA, source_url=LAQUINTA_URL,
        fetcher=fetcher, cas=MemoryCas(), observed_at="2026-08-01",
        rendered_policy_text=LAQUINTA_RENDERED)
    assert out.status == SR.ACCESS_BLOCKED


def test_rendered_evidence_cannot_rescue_a_wrong_property():
    """Identity is decided before this rule, and a page that cannot identify
    itself stays ENTITY_MISMATCH however good the rendered text is."""
    anonymous = """<html><head><title>Pet-Friendly Hotels</title></head><body>
    <div class="policy-items pet-policy">Pet &amp; Service Animal Policy</div>
    <p>%s</p></body></html>""" % ("Wyndham welcomes pets at participating hotels. " * 60)
    out = _run_rendered("https://www.wyndhamhotels.com/laquinta/about-us/pet-friendly",
                        anonymous, LAQUINTA, LAQUINTA_RENDERED)
    assert out.status == SR.ENTITY_MISMATCH
