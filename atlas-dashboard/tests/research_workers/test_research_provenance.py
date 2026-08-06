"""PTF-WORKERS-004 -- the MODEL_RESEARCH_REPORT provenance contract.

These tests encode the operator-issued authority rules for model research as
executable guarantees. The failure they exist to prevent is a single one, worth
naming plainly: a model's prose about a hotel being mistaken for the hotel's own
page, and thereby publishing a pet policy nobody ever verified.

Everything here is offline. No test in this file constructs a live provider,
reads a credential, or performs a network call.
"""

from __future__ import annotations

import pytest

from services.research_workers import research_escalation as ESC
from services.research_workers import vocabulary as V
from services.research_workers import web_research as WR
from services.research_workers.contracts import SourceDocument, content_hash

QUOTE = "Pets are welcome for a $75 fee per stay."
CITED = "https://www.staybridge.com/columbus/pet-policy"


def _report(*, ok=True, text=None, urls=((CITED, "Pet Policy", "url_citation"),)):
    return WR.WebResearchReport(
        listing_key="staybridge suites columbus",
        listing_name="Staybridge Suites Columbus",
        ok=ok,
        model=WR.APPROVED_MODEL,
        allowed_domains=("staybridge.com",),
        report_text=("The official page states: %s" % QUOTE) if text is None else text,
        discovered_urls=tuple(WR.DiscoveredUrl(url=u, title=t, origin=o)
                              for u, t, o in urls),
        observed_at="2026-08-02",
        request_id="resp_abc123",
        error="" if ok else "http_500",
    )


def _official_doc(text=QUOTE, source_type=V.SOURCE_OFFICIAL_PROPERTY):
    return SourceDocument(
        source_url=CITED, source_type=source_type, retrieved_at="2026-08-02",
        title="Pet Policy", content_text=text, content_hash=content_hash(text),
        retrieval_status=V.RETRIEVAL_OK)


# --------------------------------------------------------------------------- #
# Rule 1 -- MODEL_RESEARCH_REPORT is never equivalent to a real evidence type.
# --------------------------------------------------------------------------- #

def test_model_research_is_not_any_official_or_attested_provenance():
    mr = V.SOURCE_MODEL_RESEARCH_REPORT
    assert mr not in V.OFFICIAL_SOURCE_TYPES
    assert mr in V.NON_PUBLISHABLE_SOURCE_TYPES
    for other in (V.SOURCE_OFFICIAL_PROPERTY, V.SOURCE_OFFICIAL_BRAND,
                  V.SOURCE_OFFICIAL_FAQ, V.SOURCE_OFFICIAL_PROPERTY_INHERITED,
                  V.SOURCE_MANUAL_OFFICIAL_ATTESTATION):
        assert mr != other
    # and it can never outrank a source that IS publishable
    assert V.SOURCE_TYPE_RANK[mr] == 0


def test_research_document_is_not_usable_official_evidence():
    doc = WR.research_report_document(_report())
    doc.validate()                                  # well-formed...
    assert doc.source_type == V.SOURCE_MODEL_RESEARCH_REPORT
    assert doc.is_usable_official is False          # ...but never evidence
    # the URN must not impersonate the hotel's own URL
    assert doc.source_url.startswith("urn:atlas:model-research-report:")
    assert "staybridge.com" not in doc.source_url


# --------------------------------------------------------------------------- #
# Rule 2 -- what a report legitimately DOES contribute.
# --------------------------------------------------------------------------- #

def test_report_preserves_citations_and_locates_candidate_urls():
    r = _report()
    assert [d.url for d in r.discovered_urls] == [CITED]
    d = r.to_dict()
    assert d["is_official_evidence"] is False and d["publication_eligible"] is False
    assert d["source_type"] == V.SOURCE_MODEL_RESEARCH_REPORT


# --------------------------------------------------------------------------- #
# Rule 3 + 6 -- a claim carries two SEPARATE quote facts and publishes nothing.
# --------------------------------------------------------------------------- #

def test_fresh_claim_is_unverified_and_never_publication_eligible():
    claim = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED)
    assert claim.cited_source_quote_status == WR.QUOTE_UNVERIFIED
    assert claim.independently_retrieved is False
    assert claim.is_confirmed is False
    assert claim.publication_eligible is False
    assert claim.source_type == V.SOURCE_MODEL_RESEARCH_REPORT


def test_report_quote_check_is_scoped_to_the_report_only():
    """The rule-6 separation, stated as a test.

    The quote is verbatim in the report and absent from the official page. A
    system that conflated the two checks would call this verified; here the
    report-scoped check passes while confirmation against the real page fails.
    """
    r = _report()
    assert WR.report_quote_present(r, QUOTE) is True

    claim = WR.claim_from_report(r, report_quote=QUOTE, cited_url=CITED)
    page_that_says_something_else = _official_doc("Pets are not permitted.")
    with pytest.raises(WR.ClaimProvenanceError, match="does not appear verbatim"):
        WR.confirm_claim_with_source(claim, page_that_says_something_else)


def test_independently_retrieved_cannot_be_set_without_our_own_fetch():
    for status in (WR.QUOTE_UNVERIFIED, WR.QUOTE_RENDERED_ATTESTED,
                   WR.QUOTE_DIRECTLY_CONFIRMED):
        with pytest.raises(WR.ClaimProvenanceError, match="independently_retrieved"):
            WR.ResearchClaim(listing_key="k", report_quote=QUOTE, cited_url=CITED,
                             cited_source_quote_status=status,
                             independently_retrieved=True)


def test_unknown_quote_status_is_refused():
    with pytest.raises(WR.ClaimProvenanceError, match="unknown cited_source_quote_status"):
        WR.ResearchClaim(listing_key="k", report_quote=QUOTE, cited_url=CITED,
                         cited_source_quote_status="LOOKS_FINE_TO_ME")


# --------------------------------------------------------------------------- #
# Rule 7 -- a claim cannot be built from anything the report did not support.
# --------------------------------------------------------------------------- #

def test_claim_refuses_a_quote_absent_from_the_report():
    with pytest.raises(WR.ClaimProvenanceError, match="does not appear verbatim in the report"):
        WR.claim_from_report(_report(), report_quote="Dogs stay free.", cited_url=CITED)


def test_claim_refuses_a_url_the_search_tool_never_returned():
    """Model prose may invent URLs; only tool citations are admissible."""
    with pytest.raises(WR.ClaimProvenanceError, match="absent from discovered_urls"):
        WR.claim_from_report(_report(), report_quote=QUOTE,
                             cited_url="https://staybridge.com/invented-by-the-model")


def test_claim_refuses_a_url_the_allowlist_rejected():
    r = WR.WebResearchReport(
        listing_key="k", listing_name="n", ok=True, model=WR.APPROVED_MODEL,
        allowed_domains=("staybridge.com",), report_text=QUOTE,
        discovered_urls=(),
        rejected_urls=({"url": "https://tripadvisor.com/x", "reason": "domain_not_in_allowlist"},),
        observed_at="2026-08-02")
    with pytest.raises(WR.ClaimProvenanceError, match="rejected by the domain allowlist"):
        WR.claim_from_report(r, report_quote=QUOTE, cited_url="https://tripadvisor.com/x")


def test_claim_refuses_a_failed_research_call():
    with pytest.raises(WR.ClaimProvenanceError, match="failed research call"):
        WR.claim_from_report(_report(ok=False), report_quote=QUOTE, cited_url=CITED)


def test_claim_records_the_full_audit_chain():
    d = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED).to_dict()
    for key in ("cited_url", "cited_page_title", "report_retrieved_at", "model",
                "response_id", "citation_origin", "report_quote",
                "cited_source_quote_status", "independently_retrieved"):
        assert key in d, key
    assert d["model"] == WR.APPROVED_MODEL
    assert d["response_id"] == "resp_abc123"
    assert d["citation_origin"] == "url_citation"


# --------------------------------------------------------------------------- #
# Rule 5 -- promotion requires evidence from OUTSIDE the model.
# --------------------------------------------------------------------------- #

def test_promotion_by_retrieved_official_page():
    claim = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED)
    confirmed = WR.confirm_claim_with_source(claim, _official_doc())
    assert confirmed.cited_source_quote_status == WR.QUOTE_RETRIEVED_VERBATIM
    assert confirmed.independently_retrieved is True
    assert confirmed.is_confirmed is True
    assert confirmed.confirmed_by == CITED
    # even confirmed, the CLAIM itself still publishes nothing
    assert confirmed.publication_eligible is False
    assert confirmed.source_type == V.SOURCE_MODEL_RESEARCH_REPORT
    # promotion is pure -- the original claim is unchanged
    assert claim.cited_source_quote_status == WR.QUOTE_UNVERIFIED


def test_rendered_attestation_promotes_without_claiming_we_fetched_it():
    claim = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED)
    doc = _official_doc(source_type=V.SOURCE_MANUAL_OFFICIAL_ATTESTATION)
    confirmed = WR.confirm_claim_with_source(claim, doc, status=WR.QUOTE_RENDERED_ATTESTED)
    assert confirmed.cited_source_quote_status == WR.QUOTE_RENDERED_ATTESTED
    assert confirmed.independently_retrieved is False   # a human carried it, not us
    assert confirmed.is_confirmed is True


def test_a_research_report_cannot_confirm_a_research_claim():
    """The circularity guard. Without this, the model verifies itself."""
    r = _report()
    claim = WR.claim_from_report(r, report_quote=QUOTE, cited_url=CITED)
    with pytest.raises(WR.ClaimProvenanceError, match="cannot confirm a research claim"):
        WR.confirm_claim_with_source(claim, WR.research_report_document(r))


def test_non_official_document_cannot_confirm():
    claim = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED)
    doc = _official_doc(source_type=V.SOURCE_OTHER)
    with pytest.raises(WR.ClaimProvenanceError, match="not usable official evidence"):
        WR.confirm_claim_with_source(claim, doc)


def test_unverified_is_not_a_confirmation_status():
    claim = WR.claim_from_report(_report(), report_quote=QUOTE, cited_url=CITED)
    with pytest.raises(WR.ClaimProvenanceError, match="not a confirmation status"):
        WR.confirm_claim_with_source(claim, _official_doc(), status=WR.QUOTE_UNVERIFIED)


# --------------------------------------------------------------------------- #
# Rule 4 -- the six named next-action states, all REVIEW-capped.
# --------------------------------------------------------------------------- #

def test_all_six_action_states_exist():
    assert ESC.RESEARCH_ACTIONS == {
        "RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE", "OFFICIAL_SOURCE_LOCATED",
        "OFFICIAL_SOURCE_ACCESS_BLOCKED", "HUMAN_RENDER_CAPTURE_REQUIRED",
        "DIRECT_CONTACT_REQUIRED", "NO_APPLICABLE_OFFICIAL_POLICY_FOUND",
    }


@pytest.mark.parametrize("followup,expected", [
    (None, ESC.OFFICIAL_SOURCE_LOCATED),
    ({"ready_for_extraction": True, "status": "RETRIEVED"}, ESC.OFFICIAL_SOURCE_LOCATED),
    ({"status": "ACCESS_BLOCKED"}, ESC.OFFICIAL_SOURCE_ACCESS_BLOCKED),
    ({"status": "BROWSER_ACCESS_BLOCKED"}, ESC.OFFICIAL_SOURCE_ACCESS_BLOCKED),
    ({"status": "RENDER_REQUIRED"}, ESC.HUMAN_RENDER_CAPTURE_REQUIRED),
    ({"status": "NOT_FOUND"}, ESC.DIRECT_CONTACT_REQUIRED),
    ({"status": "ENTITY_MISMATCH"}, ESC.DIRECT_CONTACT_REQUIRED),
    ({"status": "NETWORK_ERROR"}, ESC.RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE),
])
def test_action_is_classified_from_the_retrieval_not_the_report(followup, expected):
    assert ESC.classify_research_outcome(_report(), followup) == expected


def test_no_urls_found_means_no_applicable_policy_located():
    assert ESC.classify_research_outcome(_report(urls=())) == \
        ESC.NO_APPLICABLE_OFFICIAL_POLICY_FOUND


def test_a_failed_call_is_never_reported_as_a_finding_about_the_hotel():
    """Our own transport error must not become 'this hotel has no policy'."""
    for r in (None, _report(ok=False)):
        assert ESC.classify_research_outcome(r) == \
            ESC.RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE


def test_classification_is_total_over_the_named_set():
    for followup in (None, {}, {"status": "ANYTHING_UNEXPECTED"},
                     {"status": "RETRIEVED", "ready_for_extraction": False}):
        assert ESC.classify_research_outcome(_report(), followup) in ESC.RESEARCH_ACTIONS


def test_every_action_reports_review_cap_and_no_publication():
    for followup in (None, {"status": "ACCESS_BLOCKED"}, {"status": "RENDER_REQUIRED"},
                     {"status": "NOT_FOUND"}):
        rep = ESC.research_outcome_report(_report(), followup)
        assert rep["max_route"] == "REVIEW"
        assert rep["publication_eligible"] is False
        assert rep["action"] in ESC.RESEARCH_ACTIONS
    assert ESC.research_outcome_report(_report(), {"status": "RENDER_REQUIRED"})["requires_human"] is True
    assert ESC.research_outcome_report(_report())["requires_human"] is False


# --------------------------------------------------------------------------- #
# Rule 9 -- the airlock is not weakened by any of the above.
# --------------------------------------------------------------------------- #

def test_spend_airlock_constants_are_unchanged():
    from services.research_workers import providers as P
    assert P.WEB_RESEARCH_SPEND_AUTH_ENV == "ATLAS_DEEP_RESEARCH_SPEND_AUTHORIZATION"
    assert P.WEB_RESEARCH_SPEND_AUTH_TOKEN == "YES_MAX_5_USD"
    assert WR.APPROVED_MODEL == "gpt-5.4"


def test_escalation_still_refuses_when_direct_retrieval_succeeded():
    """Rule 9's companion: research remains escalation-only."""
    with pytest.raises(ESC.EscalationBlocked, match="escalation-only"):
        ESC.require_escalation({"ready_for_extraction": True, "status": "RETRIEVED"})
