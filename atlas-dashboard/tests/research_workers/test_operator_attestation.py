"""PTF-WORKERS-006 -- offline tests for MANUAL_OFFICIAL_ATTESTATION.

No network, no browser, no model call. The Staybridge fixture carries the real
per-pet/per-stay conflict and both fee tiers, because an attestation that
silently resolved a contradiction would be worse than no attestation: it would
launder a human's convenience into official evidence.
"""

from __future__ import annotations

import pytest

from services.research_workers import operator_capture as OC
from services.research_workers import routing as R
from services.research_workers import source_retrieval as SR
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, ProposedField, WorkerResult,
)

OFFICIAL_URL = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail"

POLICY_PROSE = (
    "Pets are welcome at Staybridge Suites Columbus-Dublin. This is a dog only hotel. "
    "Up to two friendly pups under 80 lbs are welcome. "
    "Pet fee per pet is $75 plus tax for 1-7 nights. "
    "A pet fee of $150 plus tax is charged per stay for 8 or more nights. "
    "The pet fee is non-refundable. "
)
PAGE_HTML = """<html><head><title>Staybridge Suites Columbus-Dublin</title></head>
<body><h1>Staybridge Suites Columbus-Dublin</h1>
<p>6095 Emerald Parkway, Dublin, OH 43016</p><p>Phone: +1-614-734-9882</p>
<h2>Pet Policy</h2><p>%s</p>
<p>%s</p></body></html>""" % (POLICY_PROSE, "Extra amenity copy. " * 40)


class MemoryCas:
    def __init__(self):
        self.blobs = {}

    def put_bytes(self, data: bytes) -> str:
        import hashlib
        h = hashlib.sha256(data).hexdigest()
        self.blobs[h] = data
        return h


def _job(**over):
    base = dict(
        assignment_id="attest-staybridge",
        listing_key="staybridge suites columbus dublin",
        listing_name="Staybridge Suites Columbus-Dublin",
        expected_address="6095 Emerald Parkway", expected_city="Dublin",
        expected_state="OH", expected_postal_code="43016",
        expected_phone="+1-614-734-9882", official_url=OFFICIAL_URL,
        failure_reason="blocked_source", retrieval_status="ACCESS_BLOCKED")
    base.update(over)
    return OC.CaptureJob(**base)


def _payload(**over):
    base = dict(schema=OC.CAPTURE_SCHEMA, captured_at="2026-07-27T14:05:00-04:00",
                final_url=OFFICIAL_URL, title="Staybridge Suites Columbus-Dublin",
                html=PAGE_HTML, text="", extension_version="1.0.0")
    base.update(over)
    return base


def _ingest(**over):
    return OC.ingest_capture(_payload(**over), _job(), observed_at="2026-07-27")


def _affirmation(**over):
    base = dict(operator_id="jfields80", attested_at="2026-07-27T14:06:00-04:00",
                address_confirmed=True, address_observed="6095 Emerald Parkway",
                phone_confirmed=True, phone_observed="+1-614-734-9882")
    base.update(over)
    return OC.OperatorAffirmation(**base)


def _failure(**over):
    base = dict(status="ACCESS_BLOCKED", reason="blocked_source",
                artifact_path="data/worker_runs/.../retr-staybridge.json")
    base.update(over)
    return OC.AutomatedFailure(**base)


def _shots(cas=None, n=1):
    cas = cas or MemoryCas()
    return [OC.store_screenshot(cas, b"\x89PNG fake screenshot %d" % i,
                                width=1440, height=900, note="page-%d.png" % i)
            for i in range(n)]


def _build(**over):
    kw = dict(ingestion=_ingest(), job=_job(), affirmation=_affirmation(),
              automated_failure=_failure(), screenshots=_shots(),
              observed_at="2026-07-27T14:05:00-04:00",
              observed_timezone="America/New_York")
    kw.update(over)
    return OC.build_attestation(**kw)


# --------------------------------------------------------------------------- #
# PTF-CAPTURE-004 -- a citation is not an address bar.
#
# Four Hilton captures arrived carrying sessionToken=<uuid> from the operator's
# own browsing session, plus gclid/gbraid Google Ads click ids. That URL is
# published as the hotel's official source and as the /go/official-website
# target, so it would have put a personal session identifier on a consumer page.
# --------------------------------------------------------------------------- #

_TOKEN_URL = (OFFICIAL_URL + "?flexibleDates=false&numRooms=1"
              "&sessionToken=fc17ec36-bf4f-43b9-80d1-60247cc6b733")
_ADS_URL = OFFICIAL_URL + "?WT.mc_id=zlada0ww1hi2psh&gclsrc=aw.ds&gclid=CjwKCAjw7KvT"


@pytest.mark.parametrize("url,private", [
    (_TOKEN_URL, True),
    (_ADS_URL, True),
    (OFFICIAL_URL + "?utm_source=newsletter", True),
    (OFFICIAL_URL + "?numRooms=1&numAdults=1", False),
    (OFFICIAL_URL, False),
    ("", False),
])
def test_private_query_params_are_recognised(url, private):
    assert OC.url_carries_private_params(url) is private


def test_canonical_is_cited_over_the_address_bar():
    """The canonical url is the page's own statement of its address, and it is
    clean by construction."""
    out = OC.ingest_capture(
        _payload(final_url=_TOKEN_URL,
                 html=PAGE_HTML.replace("<head>", '<head><link rel="canonical" href="%s">'
                                        % OFFICIAL_URL)),
        _job(), observed_at="2026-07-27")
    assert out.accepted
    assert out.source_document.source_url == OFFICIAL_URL
    assert "sessionToken" not in out.source_document.source_url


def test_a_canonical_naming_a_different_page_is_not_borrowed():
    """Tidying a query string by adopting another page's address would misstate
    which page was actually read."""
    other = "https://www.ihg.com/staybridge/hotels/us/en/dublin/xxxxx/hoteldetail"
    assert OC._citable_url(_TOKEN_URL, other) == _TOKEN_URL
    assert OC._citable_url(_TOKEN_URL, OFFICIAL_URL) == OFFICIAL_URL
    assert OC._citable_url(_TOKEN_URL, "") == _TOKEN_URL


def test_attestation_refuses_a_citation_carrying_a_session_token():
    single = OC.ingest_capture(_payload(final_url=_TOKEN_URL), _job(),
                               observed_at="2026-07-27")
    assert single.accepted                      # the PAGE is fine
    with pytest.raises(OC.AttestationError, match="session or ad-tracking"):
        _build(ingestion=single)                # the CITATION is not


# --------------------------------------------------------------------------- #
# PTF-WORKERS-007 regression: the single-capture path did not change.
#
# Paired evidence added an optional field to the attestation. If that field
# ever appears on a single-capture record, every attestation hash issued before
# the feature existed becomes unverifiable -- so these assertions guard the
# shape, not just the behaviour.
# --------------------------------------------------------------------------- #

def test_single_capture_attested_content_has_no_paired_key():
    content = _build().attested_content()
    assert "paired_evidence" not in content


def test_single_capture_record_reports_no_paired_evidence():
    att = _build()
    assert att.paired_evidence is None
    assert "paired_evidence" not in att.to_dict()


def test_single_capture_hash_is_deterministic():
    assert _build().attestation_hash() == _build().attestation_hash()


def test_single_capture_role_is_property_not_paired():
    assert _ingest().source_role == OC.SOURCE_ROLE_PROPERTY


def test_binding_evidence_cannot_be_attached_to_a_single_capture():
    """Gate P in the other direction: binding evidence on an ordinary capture
    would be a claim nothing re-checked."""
    fake = OC.PairedEvidence(
        identity_capture_url=OFFICIAL_URL, identity_text_hash="a" * 64,
        policy_capture_url="https://www.ihg.com/search/findHotels.mi",
        policy_text_hash="b" * 64,
        matched_signals=OC.REQUIRED_BINDING_SIGNALS)
    with pytest.raises(OC.AttestationError, match="gateP"):
        _build(paired_evidence=fake)


# --------------------------------------------------------------------------- #
# Defect regressions (the two latent bugs).
# --------------------------------------------------------------------------- #

def test_captured_source_document_actually_validates():
    """The regression that would have caught both latent defects: source_type
    carried the importer relationship slug, and content_hash was a bare digest."""
    doc = _ingest().source_document
    doc.validate()
    assert doc.source_type == V.SOURCE_MANUAL_OFFICIAL_ATTESTATION
    assert doc.content_hash.startswith("sha256:")
    assert doc.is_usable_official is True


def test_capture_is_accepted_end_to_end():
    out = _ingest()
    assert out.status == OC.CAPTURE_ACCEPTED
    assert out.accepted is True
    assert out.identity == SR.EXACT_MATCH


# --------------------------------------------------------------------------- #
# Provenance: the four transports are distinguishable.
# --------------------------------------------------------------------------- #

def test_four_capture_methods_are_a_closed_distinct_vocabulary():
    assert SR.CAPTURE_METHODS == frozenset({
        "HTTP_STATIC", "BROWSER_RENDERED", "MANUAL_ATTESTATION", "MODEL_RESEARCH"})
    assert OC.CAPTURE_METHOD_MANUAL_ATTESTATION == "MANUAL_ATTESTATION"
    assert _build().capture_method == "MANUAL_ATTESTATION"


def test_manual_attestation_source_type_placement():
    t = V.SOURCE_MANUAL_OFFICIAL_ATTESTATION
    assert t in V.SOURCE_TYPES
    assert t in V.OFFICIAL_SOURCE_TYPES              # a human saw the official page
    assert t in V.NON_AUTOMATIC_SOURCE_TYPES         # but never publishes itself
    assert t not in V.PROPERTY_SPECIFIC_SOURCE_TYPES
    # ranks BELOW directly fetched property evidence
    assert V.SOURCE_TYPE_RANK[t] < V.SOURCE_TYPE_RANK[V.SOURCE_OFFICIAL_PROPERTY]
    assert V.SOURCE_TYPE_RANK[t] < V.SOURCE_TYPE_RANK[V.SOURCE_OFFICIAL_FAQ]


def test_manual_attestation_is_distinct_from_model_research():
    assert V.SOURCE_MANUAL_OFFICIAL_ATTESTATION != V.SOURCE_MODEL_RESEARCH_REPORT
    assert V.SOURCE_MODEL_RESEARCH_REPORT not in V.OFFICIAL_SOURCE_TYPES
    assert V.SOURCE_MANUAL_OFFICIAL_ATTESTATION in V.OFFICIAL_SOURCE_TYPES


# --------------------------------------------------------------------------- #
# Gate 1 -- demonstrated automated failure.
# --------------------------------------------------------------------------- #

def test_gate1_requires_a_recorded_automated_failure():
    with pytest.raises(OC.AttestationError, match="gate1"):
        _build(automated_failure=OC.AutomatedFailure(status=""))


def test_gate1_refuses_a_failure_that_does_not_justify_a_human():
    """An unsafe URL or entity mismatch must never be laundered by a person."""
    for status in ("REJECTED_UNSAFE_URL", "ENTITY_MISMATCH", "RETRIEVED"):
        with pytest.raises(OC.AttestationError, match="gate1"):
            _build(automated_failure=_failure(status=status))


@pytest.mark.parametrize("status", sorted(OC.CAPTURE_WORTHY))
def test_gate1_accepts_every_capture_worthy_failure(status):
    assert _build(automated_failure=_failure(status=status)) is not None


# --------------------------------------------------------------------------- #
# Gate 2 -- operator affirmation and timestamps.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("over", [{"operator_id": ""}, {"operator_id": "   "},
                                  {"attested_at": ""}])
def test_gate2_requires_operator_and_timestamp(over):
    with pytest.raises(OC.AttestationError, match="gate2"):
        _build(affirmation=_affirmation(**over))


@pytest.mark.parametrize("over", [{"observed_at": ""}, {"observed_timezone": ""}])
def test_gate2_requires_observation_time_and_zone(over):
    with pytest.raises(OC.AttestationError, match="gate2"):
        _build(**over)


def test_gate2_statement_cannot_be_weakened():
    with pytest.raises(OC.AttestationError, match="gate2"):
        _build(affirmation=_affirmation(statement="I glanced at it, probably fine"))


def test_operator_handle_is_the_only_identity_stored():
    d = _build().to_dict()["affirmation"]
    assert d["operator_id"] == "jfields80"
    blob = repr(_build().to_dict()).lower()
    for personal in ("@", "email", "ip_address", "hostname", "machine_name",
                     "legal_name", "full_name"):
        assert personal not in blob, "unnecessary personal data %r present" % personal


# --------------------------------------------------------------------------- #
# Gate 3 -- address and phone confirmation.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("over,msg", [
    ({"address_confirmed": False}, "gate3"),
    ({"phone_confirmed": False}, "gate3"),
])
def test_gate3_requires_both_confirmations(over, msg):
    with pytest.raises(OC.AttestationError, match=msg):
        _build(affirmation=_affirmation(**over))


def test_gate3_records_what_the_operator_observed():
    d = _build().to_dict()["affirmation"]
    assert d["address_observed"] == "6095 Emerald Parkway"
    assert d["phone_observed"] == "+1-614-734-9882"


# --------------------------------------------------------------------------- #
# Gate 4 -- CAS-backed screenshots.
# --------------------------------------------------------------------------- #

def test_gate4_requires_at_least_one_screenshot():
    with pytest.raises(OC.AttestationError, match="gate4"):
        _build(screenshots=[])


def test_gate4_rejects_a_non_cas_digest():
    bad = OC.Screenshot(sha256="not-a-digest", byte_length=10)
    with pytest.raises(OC.AttestationError, match="gate4"):
        _build(screenshots=[bad])


def test_gate4_rejects_an_empty_screenshot():
    bad = OC.Screenshot(sha256="a" * 64, byte_length=0)
    with pytest.raises(OC.AttestationError, match="gate4"):
        _build(screenshots=[bad])


def test_screenshot_bytes_go_to_cas_and_never_into_the_json():
    cas = MemoryCas()
    shots = _shots(cas, n=2)
    d = _build(screenshots=shots).to_dict()
    assert len(d["screenshots"]) == 2
    for s, ref in zip(shots, d["screenshots"]):
        assert ref["sha256"] == s.sha256
        assert cas.blobs[s.sha256]                      # bytes are in the CAS
        assert "data" not in ref and "bytes" not in ref  # ...and not in the record
    assert "PNG" not in repr(d)


def test_store_screenshot_refuses_empty_bytes():
    with pytest.raises(OC.AttestationError):
        OC.store_screenshot(MemoryCas(), b"")


def test_retention_policy_is_documented_and_separable_from_identity():
    a = _build()
    assert "indefinitely" in a.to_dict()["retention"]
    # the hash covers screenshot HASHES, not bytes, so a future retention change
    # cannot alter attestation identity
    assert a.attestation_hash() == _build().attestation_hash()


# --------------------------------------------------------------------------- #
# Gate 5 -- the model-research firewall.
# --------------------------------------------------------------------------- #

def test_gate5_a_model_research_urn_is_not_an_official_page():
    urn = "urn:atlas:model-research-report:deadbeef"
    ing = OC.ingest_capture(_payload(final_url=urn), _job(), observed_at="2026-07-27")
    # ingestion already refuses it on domain authorization
    assert ing.accepted is False
    with pytest.raises(OC.AttestationError, match="gate5"):
        _build(ingestion=ing)


def test_gate5_refuses_an_unaccepted_capture():
    rejected = OC.ingest_capture(_payload(html="<html><body>tiny</body></html>"),
                                 _job(), observed_at="2026-07-27")
    assert rejected.accepted is False
    with pytest.raises(OC.AttestationError, match="gate5"):
        _build(ingestion=rejected)


def test_gate5_refuses_content_identical_to_the_linked_model_report():
    """A report may be REFERENCED. It may never be the attested content."""
    ing = _ingest()
    ref = OC.ModelResearchRef(urn="urn:atlas:model-research-report:abc",
                              report_hash=ing.normalized_text_hash)
    with pytest.raises(OC.AttestationError, match="gate5"):
        _build(ingestion=ing, model_research_ref=ref)


def test_a_valid_model_research_link_is_reference_only():
    ref = OC.ModelResearchRef(urn="urn:atlas:model-research-report:abc",
                              report_hash="sha256:" + "f" * 64)
    a = _build(model_research_ref=ref)
    d = a.to_dict()["model_research_ref"]
    assert d["is_evidence"] is False
    assert "never attested content" in d["note"]
    # linkage does not change provenance
    assert a.source_type == V.SOURCE_MANUAL_OFFICIAL_ATTESTATION
    assert a.ingestion.source_document.source_type == V.SOURCE_MANUAL_OFFICIAL_ATTESTATION


def test_no_code_path_converts_a_model_report_into_official_evidence():
    import ast
    import inspect
    code = ast.unparse(ast.parse(inspect.getsource(OC)))
    # the attestation's content always comes from the ingested page document
    assert "MODEL_RESEARCH_REPORT" not in code
    assert V.SOURCE_MODEL_RESEARCH_REPORT not in V.OFFICIAL_SOURCE_TYPES


# --------------------------------------------------------------------------- #
# Gate 6 -- explicit, separate approval.
# --------------------------------------------------------------------------- #

def test_gate6_attestation_begins_pending_and_unpublishable():
    a = _build()
    assert a.approval.state == OC.APPROVAL_PENDING
    assert a.publishable is False
    assert a.to_dict()["publishable"] is False


def test_gate6_approval_is_a_separate_recorded_action():
    a = _build()
    approved = OC.approve_attestation(
        a, approver_id="jfields80", approved_at="2026-07-28T09:00:00-04:00",
        approval_record_id="APR-0001")
    assert approved.publishable is True
    assert approved.approval.approver_id == "jfields80"
    assert approved.approval.approved_at != a.affirmation.attested_at
    assert approved.approval.approval_record_id == "APR-0001"
    # operator and approver stay SEPARATE fields even with the same handle
    assert approved.affirmation.operator_id == approved.approval.approver_id
    d = approved.to_dict()
    assert d["affirmation"]["operator_id"] == "jfields80"
    assert d["approval"]["approver_id"] == "jfields80"


@pytest.mark.parametrize("missing", ["approver_id", "approved_at", "approval_record_id"])
def test_gate6_approval_requires_every_field(missing):
    kw = dict(approver_id="jfields80", approved_at="2026-07-28", approval_record_id="APR-1")
    kw[missing] = ""
    with pytest.raises(OC.AttestationError, match="gate6"):
        OC.approve_attestation(_build(), **kw)


def test_gate6_double_approval_is_refused():
    approved = OC.approve_attestation(_build(), approver_id="jfields80",
                                      approved_at="2026-07-28", approval_record_id="APR-1")
    with pytest.raises(OC.AttestationError):
        OC.approve_attestation(approved, approver_id="jfields80",
                               approved_at="2026-07-29", approval_record_id="APR-2")


def test_rejection_is_not_publishable():
    rejected = OC.reject_attestation(_build(), approver_id="jfields80",
                                     approved_at="2026-07-28", approval_record_id="APR-9")
    assert rejected.approval.state == OC.APPROVAL_REJECTED
    assert rejected.publishable is False


# --------------------------------------------------------------------------- #
# Immutability.
# --------------------------------------------------------------------------- #

def test_attestation_hash_is_stable_for_identical_input():
    assert _build().attestation_hash() == _build().attestation_hash()
    assert _build().attestation_hash().startswith("sha256:")


def test_approval_does_not_change_the_attested_content_hash():
    """So an approval provably applies to exactly what was attested."""
    a = _build()
    before = a.attestation_hash()
    approved = OC.approve_attestation(a, approver_id="jfields80",
                                      approved_at="2026-07-28", approval_record_id="APR-1")
    assert approved.attestation_hash() == before


@pytest.mark.parametrize("over", [
    {"observed_timezone": "UTC"},
    {"affirmation": None},
])
def test_attestation_hash_changes_when_attested_content_changes(over):
    if over.get("affirmation", "x") is None:
        over = {"affirmation": _affirmation(address_observed="somewhere else")}
    assert _build(**over).attestation_hash() != _build().attestation_hash()


def test_attestation_id_is_deterministic():
    assert _build().attestation_id == _build().attestation_id
    assert _build().attestation_id.startswith("attest-")


# --------------------------------------------------------------------------- #
# Contradiction preservation.
# --------------------------------------------------------------------------- #

def test_both_per_pet_and_per_stay_language_are_preserved():
    a = _build()
    topics = [s["topic"] for s in a.statements]
    assert "fee_basis_per_pet" in topics and "fee_basis_per_stay" in topics
    assert "conflicting_fee_basis_per_pet_vs_fee_basis_per_stay" in a.contradictions


def test_both_fee_tiers_and_conditions_are_preserved():
    a = _build()
    quotes = " ".join(s["quote"] for s in a.statements)
    assert "1-7 nights" in quotes and "8 or more nights" in quotes
    assert "plus tax" in quotes
    assert any(s["topic"] == "nonrefundable" for s in a.statements)
    assert set(a.fee_amounts) == {"75", "150"}
    assert any(c.startswith("multiple_fee_amounts") for c in a.contradictions)


def test_every_statement_is_verbatim_in_the_attested_text():
    a = _build()
    text = a.ingestion.source_document.content_text
    for s in a.statements:
        assert s["quote"] in text
    starts = [s["char_start"] for s in a.statements]
    assert starts == sorted(starts)


# --------------------------------------------------------------------------- #
# Routing.
# --------------------------------------------------------------------------- #

def _route(doc):
    quote = "Pets are welcome at Staybridge Suites Columbus-Dublin."
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key="k", listing_name="n",
        address="", official_website="", allowed_source_urls=(doc.source_url,),
        source_documents=(doc,), requested_fields=(V.FIELD_PETS_ALLOWED,),
        created_by="test")
    assignment.validate()
    assert quote in doc.content_text
    result = WorkerResult(
        assignment_id="a1", listing_key="k", status=V.STATUS_COMPLETED,
        selected_source_url=doc.source_url, selected_source_type=doc.source_type,
        evidence_quotes=(quote,),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote=quote, source_url=doc.source_url,
            source_type=doc.source_type),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="operator", model="none").with_hash()
    return R.route_result(assignment, result, observed_at="2026-07-27")


def test_an_attested_document_routes_review_never_ready():
    env = _route(_build().ingestion.source_document)
    assert env.route == R.ROUTE_REVIEW
    assert R.INHERITED_IDENTITY_REQUIRES_REVIEW in env.reason_codes
    assert env.publication_eligible is False


def test_approval_does_not_make_routing_skip_review():
    """Approval authorizes publication downstream; it never turns the airlock
    off. An approved attestation still routes REVIEW on its own merits."""
    a = OC.approve_attestation(_build(), approver_id="jfields80",
                               approved_at="2026-07-28", approval_record_id="APR-1")
    assert a.publishable is True
    env = _route(a.ingestion.source_document)
    assert env.route == R.ROUTE_REVIEW
    assert env.publication_eligible is False


# --------------------------------------------------------------------------- #
# No network / no spend on this path.
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Audit findings A and C -- regressions for real defects found by adversarial
# probing of the combined branch, not by any existing test.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fact_source_type", ["", V.SOURCE_OFFICIAL_PROPERTY,
                                              V.SOURCE_OFFICIAL_FAQ])
def test_finding_a_a_fact_cannot_escape_review_by_misdeclaring_its_source_type(
        fact_source_type):
    """A fact citing a non-automatic DOCUMENT must be withheld no matter what
    type the fact claims. The rule resolves provenance from the assignment's
    document, never from the result's own assertion."""
    doc = _build().ingestion.source_document
    quote = "Pets are welcome at Staybridge Suites Columbus-Dublin."
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key="k", listing_name="n",
        address="", official_website="", allowed_source_urls=(doc.source_url,),
        source_documents=(doc,), requested_fields=(V.FIELD_PETS_ALLOWED,),
        created_by="test")
    result = WorkerResult(
        assignment_id="a1", listing_key="k", status=V.STATUS_COMPLETED,
        selected_source_url=doc.source_url,
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,      # spoofed
        evidence_quotes=(quote,),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote=quote, source_url=doc.source_url,
            source_type=fact_source_type),),                  # blank or spoofed
        unknown_fields=(), contradictions=(), warnings=(),
        provider="p", model="m").with_hash()
    env = R.route_result(assignment, result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_REVIEW, "spoofed source_type reached %s" % env.route
    assert R.INHERITED_IDENTITY_REQUIRES_REVIEW in env.reason_codes
    assert env.publication_eligible is False


def test_finding_c_verification_detects_tampered_attested_content():
    record = _build().to_dict()
    assert OC.verify_attestation_record(record) == (True, "")
    tampered = dict(record)
    tampered["official_url"] = "https://www.example.com/somewhere-else"
    ok, reason = OC.verify_attestation_record(tampered)
    assert ok is False
    assert "modified since it was attested" in reason


def test_finding_c_approval_refuses_a_tampered_record():
    record = _build().to_dict()
    record["listing_name"] = "A Different Hotel"
    with pytest.raises(OC.AttestationError, match="modified since"):
        OC.approve_attestation_record(
            record, approver_id="jfields80", approved_at="2026-07-28",
            approval_record_id="APR-1")


def test_finding_c_stored_record_approval_preserves_the_hash():
    record = _build().to_dict()
    before = record["attestation_hash"]
    approved = OC.approve_attestation_record(
        record, approver_id="jfields80", approved_at="2026-07-28T09:00:00-04:00",
        approval_record_id="APR-0001")
    assert approved["attestation_hash"] == before
    assert approved["approval"]["state"] == OC.APPROVAL_APPROVED
    assert approved["publishable"] is True
    assert OC.verify_attestation_record(approved) == (True, "")
    # the attested content is untouched
    assert OC.attested_content_from_record(approved) == \
        OC.attested_content_from_record(record)


@pytest.mark.parametrize("missing", ["approver_id", "approved_at", "approval_record_id"])
def test_finding_c_stored_approval_enforces_gate6(missing):
    kw = dict(approver_id="jfields80", approved_at="2026-07-28", approval_record_id="APR-1")
    kw[missing] = ""
    with pytest.raises(OC.AttestationError, match="gate6"):
        OC.approve_attestation_record(_build().to_dict(), **kw)


def test_finding_c_double_approval_is_refused_on_the_stored_path():
    approved = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-07-28",
        approval_record_id="APR-1")
    with pytest.raises(OC.AttestationError, match="not PENDING"):
        OC.approve_attestation_record(approved, approver_id="jfields80",
                                      approved_at="2026-07-29",
                                      approval_record_id="APR-2")


def test_finding_c_rejection_is_recorded_and_unpublishable():
    rejected = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-07-28",
        approval_record_id="APR-9", reject=True)
    assert rejected["approval"]["state"] == OC.APPROVAL_REJECTED
    assert rejected["publishable"] is False


def test_finding_c_a_record_without_a_hash_cannot_be_approved():
    record = _build().to_dict()
    record.pop("attestation_hash")
    with pytest.raises(OC.AttestationError, match="no attestation_hash"):
        OC.approve_attestation_record(record, approver_id="jfields80",
                                      approved_at="2026-07-28",
                                      approval_record_id="APR-1")


def test_attestation_path_has_no_network_or_credential_access():
    import ast
    import inspect
    code = ast.unparse(ast.parse(inspect.getsource(OC)))
    # Names that can actually open a connection or read a secret. `urllib.parse`
    # is deliberately NOT banned -- urlsplit is a pure string parser and the
    # module needs it; banning the whole `urllib` package would be a slogan
    # rather than a control.
    for banned in ("import requests", "urllib.request", "urlopen", "http.client",
                   "import socket", "OPENAI_API_KEY", "os.environ",
                   "build_provider", "playwright", "/v1/responses"):
        assert banned not in code, "%r reachable from the attestation path" % banned


# --------------------------------------------------------------------------- #
# PTF-CAPTURE-003F -- an approval that overrides an observation must say why.
# --------------------------------------------------------------------------- #

def test_approval_rationale_is_recorded_beside_the_decision():
    """Aloft was approved over preserved `multiple_fee_amounts` on the
    judgement that the page-wide amounts were a promo and a guest review, not
    pet-policy terms. That judgement is the whole basis of the approval; kept
    only in someone's memory it cannot be reviewed later."""
    why = ("page-wide 100/150 are promotional and review copy outside the "
           "Pets card; $50/night and a $150/stay maximum are complementary")
    approved = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-08-01",
        approval_record_id="APR-ALOFT-CMHCO-001", rationale=why)
    assert approved["approval"]["rationale"] == why
    assert approved["approval"]["state"] == OC.APPROVAL_APPROVED


def test_rationale_does_not_disturb_the_attested_content_or_its_hash():
    record = _build().to_dict()
    before = record["attestation_hash"]
    approved = OC.approve_attestation_record(
        record, approver_id="jfields80", approved_at="2026-08-01",
        approval_record_id="APR-1", rationale="x" * 400)
    assert approved["attestation_hash"] == before
    assert OC.verify_attestation_record(approved) == (True, "")
    assert OC.attested_content_from_record(approved) == \
        OC.attested_content_from_record(record)


def test_rationale_is_optional_and_absent_rather_than_empty():
    """Approvals that need no explanation must not carry a hollow field that
    later reads as 'a reason was given'."""
    approved = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-08-01",
        approval_record_id="APR-2")
    assert "rationale" not in approved["approval"]
    blank = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-08-01",
        approval_record_id="APR-3", rationale="   ")
    assert "rationale" not in blank["approval"]


def test_a_rejection_can_also_carry_its_grounds():
    rejected = OC.approve_attestation_record(
        _build().to_dict(), approver_id="jfields80", approved_at="2026-08-01",
        approval_record_id="APR-4", reject=True,
        rationale="policy block names a different property")
    assert rejected["approval"]["state"] == OC.APPROVAL_REJECTED
    assert "different property" in rejected["approval"]["rationale"]
    assert rejected["publishable"] is False
