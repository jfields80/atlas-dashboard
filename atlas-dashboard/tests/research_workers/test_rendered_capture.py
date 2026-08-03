"""PTF-WORKERS-005 -- offline tests for browser-rendered capture orchestration.

No browser, no network, no model call. The Staybridge fixture reproduces the
real wording confirmed by manual research -- including the per-pet/per-stay
contradiction and both stay-length fee tiers -- because preserving exactly
that is the point of this sprint. The gpt-5.4 research proof collapsed the
contradiction and flattened "$75 / $150" into "75 to 150 dollars"; these tests
exist to guarantee the rendered path does not.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.importer import browser_fetch as BF
from scripts.pettripfinder.importer import constants as C
from services.research_workers import rendered_capture as RC
from services.research_workers import routing as R
from services.research_workers import source_retrieval as SR
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, ProposedField, WorkerResult,
)

PARENT_URL = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail"
CHILD_URL = PARENT_URL + "/amenities"
ALLOWED = ("ihg.com",)

EXPECTED = SR.ExpectedEntity(
    listing_key="staybridge suites columbus dublin",
    listing_name="Staybridge Suites Columbus-Dublin",
    address="6095 Emerald Parkway", city="Dublin", state="OH",
    postal_code="43016", phone="+1-614-734-9882",
    website_url=PARENT_URL)

# The real policy wording. Note the deliberate internal conflict: the fee is
# described "per pet" in one sentence and "per stay" in another.
POLICY_PROSE = (
    "This is a dog only hotel. Up to two friendly pups under 80 lbs are welcome. "
    "Pet fee per pet is $75 plus tax for 1-7 nights. "
    "A pet fee of $150 plus tax is charged per stay for 8 or more nights. "
    "The pet fee is non-refundable. "
)

# Parent page: identifies itself (name + address + phone).
PARENT_HTML = """<html><head><title>Staybridge Suites Columbus-Dublin</title></head>
<body><h1>Staybridge Suites Columbus-Dublin</h1>
<p>6095 Emerald Parkway, Dublin, OH 43016</p><p>Phone: +1-614-734-9882</p>
<p>Pets are welcome at Staybridge Suites Columbus-Dublin. %s</p></body></html>""" % POLICY_PROSE

# Child page: carries the SAME policy but names neither the property, nor its
# address, nor its phone -- exactly why an /amenities page cannot identify
# itself. Its only tie to the property is the code in its URL.
CHILD_HTML = """<html><head><title>Hotel Amenities</title></head>
<body><h2>Pet Policy</h2><p>Pets are welcome at this property. %s</p>
<p>Additional amenities include free breakfast and laundry.</p></body></html>""" % POLICY_PROSE


class MemoryCas:
    def __init__(self):
        self.blobs = {}

    def put_bytes(self, data: bytes) -> str:
        import hashlib
        h = hashlib.sha256(data).hexdigest()
        self.blobs[h] = data
        return h


class MultiPageDriver:
    """Serves canned rendered pages by URL. One instance == one browser run."""

    def __init__(self, pages, status=200, unstable=False):
        self._pages = dict(pages)
        self._status = status
        self._unstable = unstable
        self.calls = []

    def render(self, url, *, navigation_timeout_ms, total_budget_ms, expand_content):
        self.calls.append(url)
        html = self._pages.get(url)
        if html is None:
            return BF.BrowserRenderResult(url, final_url=url, http_status=404,
                                          content_type="text/html")
        text = _visible(html)
        second = text + (" Rooms left: 2. " * 300 if self._unstable else "")
        return BF.BrowserRenderResult(
            requested_url=url, final_url=url, http_status=self._status,
            content_type="text/html; charset=utf-8",
            transport_body=b"<html><body>pre-js shell</body></html>",
            dom_html=html, dom_html_second=html,
            visible_text=text, visible_text_second=second)


def _visible(html: str) -> str:
    from scripts.pettripfinder.importer.source_snapshot import normalize_html_to_text
    return normalize_html_to_text(html)[0]


def _capture(pages=None, **kw):
    pages = pages if pages is not None else {PARENT_URL: PARENT_HTML, CHILD_URL: CHILD_HTML}
    driver = MultiPageDriver(pages, **kw)
    fetcher = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    return RC.capture_rendered_source(
        expected=EXPECTED, child_url=CHILD_URL, fetcher=fetcher, cas=MemoryCas(),
        observed_at="2026-07-27", assignment_id="rend-staybridge"), driver


# --------------------------------------------------------------------------- #
# Property code + parent resolution.
# --------------------------------------------------------------------------- #

def test_property_code_is_extracted_deterministically():
    assert RC.extract_property_code(PARENT_URL) == "cmhtc"
    assert RC.extract_property_code(CHILD_URL) == "cmhtc"
    assert RC.extract_property_code("https://www.ihg.com/dublin-ohio") == ""


def test_parent_url_is_derived_from_the_child():
    assert RC.parent_url_for(CHILD_URL) == PARENT_URL
    assert RC.parent_url_for(PARENT_URL) == ""          # already the parent
    assert RC.parent_url_for("https://www.ihg.com/dublin-ohio") == ""


def test_model_research_urn_is_refused_as_a_render_target():
    fetcher = BF.BrowserPageFetcher(MultiPageDriver({}), allowed_domains=ALLOWED,
                                    resolve_host=False)
    with pytest.raises(ValueError):
        RC.capture_rendered_source(
            expected=EXPECTED, child_url=BF.MODEL_RESEARCH_URN_PREFIX + "abc",
            fetcher=fetcher, cas=MemoryCas(), observed_at="2026-07-27",
            assignment_id="x")


# --------------------------------------------------------------------------- #
# The eight inheritance conditions.
# --------------------------------------------------------------------------- #

def _anchor(**over):
    base = dict(parent_url=PARENT_URL, parent_identity=SR.EXACT_MATCH,
                property_code="cmhtc", parent_redirect_chain=(),
                same_browser_context=True, same_run=True)
    base.update(over)
    return SR.ParentIdentity(**base)


def test_all_eight_conditions_satisfied_permits_inheritance():
    ok, reasons = SR.evaluate_inherited_identity(
        parent=_anchor(), child_final_url=CHILD_URL, child_text=POLICY_PROSE)
    assert ok is True
    assert reasons[0].startswith("identity_inherited_from_parent:")


@pytest.mark.parametrize("over,child,failure", [
    ({"parent_identity": SR.STRONG_MATCH}, CHILD_URL, "parent_not_exact_match"),
    ({"parent_identity": SR.AMBIGUOUS}, CHILD_URL, "parent_not_exact_match"),
    ({}, "https://secure.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail/amenities",
     "different_origin"),
    ({"property_code": ""}, CHILD_URL, "property_code_missing_or_mismatched"),
    ({"property_code": "zzzzz"}, CHILD_URL, "property_code_missing_or_mismatched"),
    ({}, "https://www.ihg.com/staybridge/hotels/us/en/columbus/cmhtc/other",
     "child_not_beneath_parent_path"),
    ({"same_browser_context": False}, CHILD_URL, "not_same_browser_context_and_run"),
    ({"same_run": False}, CHILD_URL, "not_same_browser_context_and_run"),
])
def test_each_condition_blocks_inheritance_on_its_own(over, child, failure):
    ok, reasons = SR.evaluate_inherited_identity(
        parent=_anchor(**over), child_final_url=child, child_text=POLICY_PROSE)
    assert ok is False
    assert failure in reasons


def test_a_redirect_to_a_different_property_blocks_inheritance():
    ok, reasons = SR.evaluate_inherited_identity(
        parent=_anchor(), child_final_url=CHILD_URL, child_text=POLICY_PROSE,
        child_redirect_chain=(
            "https://www.ihg.com/staybridge/hotels/us/en/columbus/cmhad/hoteldetail",))
    assert ok is False
    assert "redirected_to_different_property" in reasons


def test_every_failing_condition_is_reported_not_just_the_first():
    ok, reasons = SR.evaluate_inherited_identity(
        parent=_anchor(parent_identity=SR.AMBIGUOUS, property_code="",
                       same_run=False),
        child_final_url="https://other.example.com/x", child_text="")
    assert ok is False
    assert len(reasons) >= 4


# --------------------------------------------------------------------------- #
# End-to-end capture.
# --------------------------------------------------------------------------- #

def test_child_alone_cannot_identify_itself_but_inherits_from_the_parent():
    result, driver = _capture()
    assert driver.calls[0] == CHILD_URL          # child tried first
    assert PARENT_URL in driver.calls            # parent captured for identity
    assert result.parent_identity == SR.EXACT_MATCH
    assert result.outcome.identity == SR.INHERITED_FROM_PARENT
    assert result.outcome.identity_basis == "inherited_from_parent"
    assert result.outcome.parent_url == PARENT_URL


def test_inherited_capture_is_extractable_and_labeled():
    result, _ = _capture()
    out = result.outcome
    assert out.status == SR.RETRIEVED
    assert out.ready_for_extraction is True                    # may support extraction
    assert out.source_document.source_type == V.SOURCE_OFFICIAL_PROPERTY_INHERITED
    assert "identity_inherited_requires_human_confirmation" in out.warnings


def test_capture_method_is_recorded_as_browser_rendered():
    result, _ = _capture()
    assert result.outcome.capture_method == SR.CAPTURE_METHOD_BROWSER_RENDERED
    assert result.to_dict()["capture_method"] == BF.CAPTURE_METHOD_BROWSER_RENDERED


def test_artifact_records_parent_child_basis_and_redirects():
    """Approved condition 7."""
    d = _capture()[0].to_dict()
    assert d["parent_url"] == PARENT_URL
    assert d["child_url"] == CHILD_URL
    assert d["outcome"]["identity_basis"] == "inherited_from_parent"
    assert d["outcome"]["identity"] == SR.INHERITED_FROM_PARENT
    assert "redirect_chain" in d["outcome"]
    assert d["child_capture"]["redirect_chain"] == []


def test_artifact_states_the_dom_hash_is_point_in_time_only():
    notes = _capture()[0].to_dict()["hash_notes"]
    assert "POINT-IN-TIME" in notes["rendered_dom_hash"].upper()
    assert "not a reproducibility guarantee" in notes["rendered_dom_hash"].lower()
    assert "evidence anchor" in notes["normalized_text_hash"]


def test_three_hashes_are_all_present_on_a_successful_capture():
    result, _ = _capture()
    cap = result.child_capture
    assert len(cap.raw_transport_hash) == 64
    assert len(cap.rendered_dom_hash) == 64
    assert len(result.outcome.normalized_text_hash) == 64
    assert cap.raw_transport_hash != cap.rendered_dom_hash


def test_a_self_identifying_page_does_not_need_a_parent_capture():
    driver = MultiPageDriver({PARENT_URL: PARENT_HTML})
    fetcher = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    result = RC.capture_rendered_source(
        expected=EXPECTED, child_url=PARENT_URL, fetcher=fetcher, cas=MemoryCas(),
        observed_at="2026-07-27", assignment_id="rend-parent")
    assert result.outcome.identity == SR.EXACT_MATCH
    assert result.outcome.identity_basis == "self"
    assert result.outcome.source_document.source_type == V.SOURCE_OFFICIAL_PROPERTY
    assert driver.calls == [PARENT_URL]           # no parent lookup needed


def test_an_unstable_render_is_withheld():
    result, _ = _capture(unstable=True)
    assert result.outcome.status == SR.RENDER_UNSTABLE
    assert result.outcome.ready_for_extraction is False


def test_a_blocked_child_does_not_trigger_a_parent_capture():
    """No point paying a second render when the first was blocked outright."""
    result, driver = _capture(status=403)
    assert result.outcome.status == SR.ACCESS_BLOCKED
    assert driver.calls == [CHILD_URL]


# --------------------------------------------------------------------------- #
# Contradiction preservation -- the core requirement.
# --------------------------------------------------------------------------- #

def test_both_per_pet_and_per_stay_wording_are_preserved():
    result, _ = _capture()
    topics = [s.topic for s in result.statements]
    assert "fee_basis_per_pet" in topics
    assert "fee_basis_per_stay" in topics
    quotes = " ".join(s.quote for s in result.statements)
    assert "per pet" in quotes
    assert "per stay" in quotes


def test_the_contradiction_is_named_and_never_resolved():
    """A real conflict is still named and still left unresolved.

    PTF-WYNDHAM: this fixture's conflict is its two competing AMOUNTS, not its
    per-pet/per-stay wording -- those describe different dimensions of one fee.
    The marker is reported, never a resolution.
    """
    result, _ = _capture()
    assert any(c.startswith("multiple_fee_amounts") for c in result.contradictions)
    assert ("conflicting_fee_basis_per_pet_vs_fee_basis_per_stay"
            not in result.contradictions)
    # Same-axis wording still conflicts, so the rule narrowed rather than went away.
    from services.research_workers.rendered_capture import (
        collect_statements, detect_contradictions,
    )
    same_axis = detect_contradictions(collect_statements(
        "A fee of 25 USD per night applies. A fee of 75 USD per stay applies."))
    assert "conflicting_fee_basis_per_stay_vs_fee_basis_per_night" in same_axis


def test_both_fee_tiers_survive_with_amounts_and_tax_language():
    result, _ = _capture()
    quotes = " ".join(s.quote for s in result.statements)
    assert "75" in quotes and "150" in quotes
    assert "1-7 nights" in quotes
    assert "8 or more nights" in quotes
    assert "plus tax" in quotes
    assert any(s.topic == "nonrefundable" for s in result.statements)
    assert any(c.startswith("multiple_fee_amounts") for c in result.contradictions)


def test_statements_are_in_document_order_with_offsets():
    result, _ = _capture()
    starts = [s.char_start for s in result.statements]
    assert starts == sorted(starts)
    text = result.outcome.source_document.content_text
    for s in result.statements:
        assert s.quote in text                  # every quote is verbatim


def test_no_first_match_wins_every_occurrence_is_kept():
    text = ("Pet fee per pet is $75. Another line. The pet fee is charged per pet again. "
            "A $150 fee applies per stay.")
    statements = RC.collect_statements(text)
    per_pet = [s for s in statements if s.topic == "fee_basis_per_pet"]
    assert len(per_pet) >= 2, "a second per-pet sentence was dropped"
    amounts = [s for s in statements if s.topic == "fee_amount"]
    assert len(amounts) >= 2


def test_quotes_respect_the_evidence_cap():
    long_text = "Pets are welcome per pet " + ("x" * 5000) + "."
    for s in RC.collect_statements(long_text):
        assert len(s.quote) <= C.EVIDENCE_QUOTE_CAP


# --------------------------------------------------------------------------- #
# Routing: inherited identity forces REVIEW.
# --------------------------------------------------------------------------- #

def _route(doc, source_type, quote="Pets are welcome at this property."):
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key=EXPECTED.listing_key,
        listing_name=EXPECTED.listing_name, address="", official_website="",
        allowed_source_urls=(doc.source_url,), source_documents=(doc,),
        requested_fields=(V.FIELD_PETS_ALLOWED,), created_by="test")
    assignment.validate()
    # The quote must be verbatim in THIS document or the pre-existing integrity
    # gate rejects the bundle before the new rule is ever reached.
    assert quote in doc.content_text
    result = WorkerResult(
        assignment_id="a1", listing_key=EXPECTED.listing_key, status=V.STATUS_COMPLETED,
        selected_source_url=doc.source_url, selected_source_type=source_type,
        evidence_quotes=(quote,),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote=quote, source_url=doc.source_url, source_type=source_type),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="browser", model="none").with_hash()
    return R.route_result(assignment, result, observed_at="2026-07-27")


def test_the_rendered_document_is_contract_valid():
    """Regression for the latent defect where source_type carried the importer
    relationship slug and would have failed SourceDocument.validate()."""
    doc = _capture()[0].outcome.source_document
    doc.validate()
    assert doc.source_type in V.SOURCE_TYPES
    assert doc.is_usable_official is True


def test_inherited_identity_forces_review_never_ready():
    doc = _capture()[0].outcome.source_document
    env = _route(doc, V.SOURCE_OFFICIAL_PROPERTY_INHERITED)
    assert env.route == R.ROUTE_REVIEW
    assert R.INHERITED_IDENTITY_REQUIRES_REVIEW in env.reason_codes
    assert env.publication_eligible is False


def test_a_self_identified_rendered_capture_can_still_reach_ready():
    """The new rule must withhold inherited identity only -- an ordinary
    rendered capture that identifies itself is unaffected."""
    driver = MultiPageDriver({PARENT_URL: PARENT_HTML})
    fetcher = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    result = RC.capture_rendered_source(
        expected=EXPECTED, child_url=PARENT_URL, fetcher=fetcher, cas=MemoryCas(),
        observed_at="2026-07-27", assignment_id="rend-parent")
    env = _route(result.outcome.source_document, V.SOURCE_OFFICIAL_PROPERTY,
                 quote="Pets are welcome at Staybridge Suites Columbus-Dublin.")
    assert env.route == R.ROUTE_READY


@pytest.mark.parametrize("fact_source_type", ["", V.SOURCE_OFFICIAL_PROPERTY])
def test_inherited_identity_cannot_escape_review_by_misdeclaring_the_fact_type(
        fact_source_type):
    """Audit finding A. Provenance is resolved from the assignment's document,
    so a blank or spoofed fact source_type cannot reach READY."""
    doc = _capture()[0].outcome.source_document
    quote = "Pets are welcome at this property."
    assignment = Assignment(
        assignment_id="a1", market_slug="columbus", listing_key=EXPECTED.listing_key,
        listing_name=EXPECTED.listing_name, address="", official_website="",
        allowed_source_urls=(doc.source_url,), source_documents=(doc,),
        requested_fields=(V.FIELD_PETS_ALLOWED,), created_by="test")
    result = WorkerResult(
        assignment_id="a1", listing_key=EXPECTED.listing_key, status=V.STATUS_COMPLETED,
        selected_source_url=doc.source_url,
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=(quote,),
        proposed_facts=(ProposedField(
            field_name=V.FIELD_PETS_ALLOWED, state=V.SUPPORTED, value="true",
            evidence_quote=quote, source_url=doc.source_url,
            source_type=fact_source_type),),
        unknown_fields=(), contradictions=(), warnings=(),
        provider="browser", model="none").with_hash()
    env = R.route_result(assignment, result, observed_at="2026-07-27")
    assert env.route == R.ROUTE_REVIEW
    assert R.INHERITED_IDENTITY_REQUIRES_REVIEW in env.reason_codes


def test_inherited_source_type_is_official_but_not_automatic():
    assert V.SOURCE_OFFICIAL_PROPERTY_INHERITED in V.OFFICIAL_SOURCE_TYPES
    assert V.SOURCE_OFFICIAL_PROPERTY_INHERITED in V.NON_AUTOMATIC_SOURCE_TYPES
    assert V.SOURCE_OFFICIAL_PROPERTY_INHERITED not in V.PROPERTY_SPECIFIC_SOURCE_TYPES
    # never outranks a page that identifies itself
    assert (V.SOURCE_TYPE_RANK[V.SOURCE_OFFICIAL_PROPERTY_INHERITED]
            < V.SOURCE_TYPE_RANK[V.SOURCE_OFFICIAL_PROPERTY])


def test_no_model_call_and_no_credential_read_on_this_path():
    import ast
    import inspect
    src = inspect.getsource(RC) + inspect.getsource(BF)
    tree = ast.parse(inspect.getsource(RC))
    code = ast.unparse(tree)
    for banned in ("OPENAI_API_KEY", "build_provider", "LiveAuthorization",
                   "/v1/responses", "chat/completions", "os.environ"):
        assert banned not in code, "%r reachable from the rendered path" % banned
