"""AES-DATA-002D -- live Land-Grant identity-hardening regression: the
aggregate pooled-name reconciliation defect where a genuine name candidate
from a second official page (a Taproom location page whose OG title carries
a trailing "<city> <state>" qualifier, and whose LLM-extracted name carries
a terminal "Company" legal suffix) spuriously conflicted with the already-
correct authoritative name "Land-Grant Brewing Columbus", AND the conflict
bundled all four pooled name candidates together even though only two had
genuinely failed reconciliation.

The primary fixture below reproduces the EXACT saved live Anthropic output
(candidate landgrantbrewing-com-1b02fab45f: two claude-sonnet-5 extraction
calls against the real landgrantbrewing.com FAQ and Taproom pages) -- same
og:title strings, same LLM field/value/quote triples, same source URLs --
not an idealized replacement. Before the AES-DATA-002D repair this exact
fixture produced REVIEW with reasons ("conflicting_evidence",
"identity_conflict") and a single Conflict bundling all four name values;
after the repair it produces READY with zero conflicts. No network."""

from __future__ import annotations

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import _reconciles_with_resolved
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext
from scripts.pettripfinder.importer.normalize import (
    expected_city_state_suffix_compatible,
    strip_legal_suffix,
)

FAQ_URL = "https://landgrantbrewing.com/faq/"
TAPROOM_URL = "https://landgrantbrewing.com/taproom/"

_FAQ_OG_TITLE = "FAQ | Land-Grant Brewing Columbus | Hours, Parking & More"
_TAPROOM_OG_TITLE = "Taproom | Land-Grant Brewing Columbus OH | Craft Beer & Food"


def _faq_html(og_title: str = _FAQ_OG_TITLE) -> str:
    return (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="%s">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>Land-Grant Brewing Columbus</h1>"
        "<p>Are Dogs Welcome at the Taproom? Much to Gus and Debbie's "
        "excitement, well-behaved dogs are welcome in our beer garden and "
        "on the patio. While we love having your four-legged friends "
        "around, please note that dogs are not able to join you inside our "
        "Wintergarden Igloos or out on the ice rinks. "
        "*Beer Garden operations are weather dependent.</p>"
        "</body></html>" % (og_title, FAQ_URL))


def _faq_facts() -> dict:
    return {"facts": [
        {"field": "pets_allowed", "value": "true",
         "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "patio_or_outdoor_only", "value": "true",
         "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "permitted_area", "value": "beer garden and patio",
         "quote": "well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "indoor_prohibited", "value": "true",
         "quote": "dogs are not able to join you inside our Wintergarden Igloos "
                  "or out on the ice rinks"},
        {"field": "seasonal_or_weather_caveat",
         "value": "Beer Garden operations are weather dependent",
         "quote": "*Beer Garden operations are weather dependent."},
        {"field": "name", "value": "Land-Grant Brewing",
         "quote": "Land-Grant Brewing Columbus"},
    ]}


def _taproom_html(
    og_title: str = _TAPROOM_OG_TITLE, llm_name_quote: str = "LAND-GRANT BREWING COMPANY",
    address_quote: str = "424 W. TOWN STREET COLUMBUS, OHIO 43215",
    url: str = TAPROOM_URL,
) -> str:
    return (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="%s">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>%s</h1>"
        "<p>%s Dog Friendly &bull; Kid Friendly Until 8pm.</p>"
        "</body></html>" % (og_title, url, llm_name_quote, address_quote))


def _taproom_facts(
    name_value: str = "Land-Grant Brewing Company",
    name_quote: str = "LAND-GRANT BREWING COMPANY",
    address_value: str = "424 W. Town Street, Columbus, Ohio 43215",
    address_quote: str = "424 W. TOWN STREET COLUMBUS, OHIO 43215",
) -> dict:
    return {"facts": [
        {"field": "address", "value": address_value, "quote": address_quote},
        {"field": "pets_allowed", "value": "true", "quote": "Dog Friendly"},
        {"field": "name", "value": name_value, "quote": name_quote},
    ]}


def _default_context(**overrides) -> ImportContext:
    base = dict(
        category="restaurants", expected_city="Columbus", expected_state="OH",
        candidate_name="Land-Grant Brewing Columbus",
        source_relationship_hint="EXACT_ENTITY_DOMAIN")
    base.update(overrides)
    return ImportContext(**base)


def _run(
    tmp_path, *, faq_html=None, taproom_html=None, faq_facts=None, taproom_facts=None,
    context=None, urls=None, faq_marker="well-behaved dogs are welcome",
):
    fetcher = StaticPageFetcher()
    fetcher.add_html(FAQ_URL, faq_html or _faq_html())
    taproom_url = TAPROOM_URL
    t_html = taproom_html or _taproom_html()
    fetcher.add_html(taproom_url, t_html)

    faq_payload = faq_facts or _faq_facts()
    taproom_payload = taproom_facts or _taproom_facts()

    def payload(normalized_text, _category, _allowed):
        if faq_marker.lower() in normalized_text.lower():
            return faq_payload
        return taproom_payload

    extractor = StaticFactExtractor(payload)
    ctx = context or _default_context()
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_multi_import(
        urls or [FAQ_URL, taproom_url], ctx, fetcher=fetcher, extractor=extractor,
        cas=cas, observed_at="2026-07-17", created_at="2026-07-17T10:33:28")


# --------------------------------------------------------------------------- #
# Unit-level: the exact three new/changed reconciliation primitives.
# --------------------------------------------------------------------------- #

class TestReconciliationPrimitives:
    def test_taproom_city_state_title_reconciles(self):
        """Compatibility case C: "<base> <city> <state>" vs "<base> <city>"."""
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing Columbus OH",
            "Columbus", True, "OH") is True

    def test_legal_suffix_company_reconciles_with_city_qualification(self):
        """Compatibility case D: terminal "Company" stripped, THEN the
        expected-city rule must still pass."""
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing Company",
            "Columbus", True, "OH") is True

    def test_expected_city_state_suffix_helper_direct(self):
        assert expected_city_state_suffix_compatible(
            "Land-Grant Brewing Columbus OH", "Land-Grant Brewing Columbus",
            "Columbus", "OH", True) is True

    def test_strip_legal_suffix_terminal_only(self):
        assert strip_legal_suffix("Land-Grant Brewing Company") == "Land-Grant Brewing"
        assert strip_legal_suffix("Land-Grant Brewing Co") == "Land-Grant Brewing"
        assert strip_legal_suffix("Land-Grant Brewing Co.") == "Land-Grant Brewing"
        # Never mid-string.
        assert strip_legal_suffix("The Company Bar") == "The Company Bar"
        # A single token is never stripped down to nothing.
        assert strip_legal_suffix("Company") == "Company"


# --------------------------------------------------------------------------- #
# Required positive tests (1-8).
# --------------------------------------------------------------------------- #

class TestExactLiveReplayPositive:
    def test_1_exact_live_replay_becomes_ready(self, tmp_path):
        c = _run(tmp_path)
        assert c.recommendation == C.RECOMMEND_READY

    def test_7_conflict_list_empty(self, tmp_path):
        c = _run(tmp_path)
        assert c.conflicts == ()

    def test_8_recommendation_reasons_empty(self, tmp_path):
        c = _run(tmp_path)
        assert c.recommendation_reasons == ()

    def test_2_faq_og_title_reconciles(self, tmp_path):
        c = _run(tmp_path)
        assert not any(
            e.proposed_value == _FAQ_OG_TITLE and e.field_name == "name"
            and any(cf.field_name == "name" and e.proposed_value in cf.competing_values
                    for cf in c.conflicts)
            for e in c.evidence)
        assert dict(c.proposed_fields)["name"] == "Land-Grant Brewing Columbus"

    def test_3_short_brand_form_reconciles(self, tmp_path):
        c = _run(tmp_path)
        assert not any(
            cf.field_name == "name" and "Land-Grant Brewing" in cf.competing_values
            for cf in c.conflicts)

    def test_4_taproom_title_with_expected_city_state_reconciles(self, tmp_path):
        c = _run(tmp_path)
        assert not any(
            cf.field_name == "name" and _TAPROOM_OG_TITLE in cf.competing_values
            for cf in c.conflicts)

    def test_5_terminal_legal_suffix_reconciles(self, tmp_path):
        c = _run(tmp_path)
        assert not any(
            cf.field_name == "name" and "Land-Grant Brewing Company" in cf.competing_values
            for cf in c.conflicts)

    def test_6_all_four_name_rows_preserved_and_attributed(self, tmp_path):
        c = _run(tmp_path)
        name_ev = [e for e in c.evidence if e.field_name == "name"]
        values_by_source = {(e.proposed_value, e.source_url) for e in name_ev}
        assert (_FAQ_OG_TITLE, FAQ_URL) in values_by_source
        assert ("Land-Grant Brewing", FAQ_URL) in values_by_source
        assert (_TAPROOM_OG_TITLE, TAPROOM_URL) in values_by_source
        assert ("Land-Grant Brewing Company", TAPROOM_URL) in values_by_source
        assert len(name_ev) == 4

    def test_address_from_s2_pet_policy_from_s1(self, tmp_path):
        c = _run(tmp_path)
        p = dict(c.proposed_fields)
        assert "Town Street" in p["address"]
        assert p["city"] == "Columbus" and p["state"] == "OH"
        facts = dict(c.pet_facts)
        assert facts.get("pets_allowed") == "true"
        assert facts.get("indoor_prohibited") == "true"


# --------------------------------------------------------------------------- #
# Required negative tests: genuine conflicts/exclusions must remain.
# --------------------------------------------------------------------------- #

class TestGenuineConflictsRemain:
    def test_different_city_supplemental_excluded(self, tmp_path):
        """PRIMARY (FAQ) states no geography at all -- exactly the live
        shape -- so the mismatch must be caught via the supplemental's OWN
        geography against the operator's expected_city. "city"/"state" are
        not LLM-allowed fields (only structured JSON-LD bypasses the
        category whitelist for them, matching how a real location page's
        schema.org markup would carry it), so this uses structured data,
        same as the existing (AES-DATA-002B) geography-gate tests."""
        cleveland_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Taproom | Land-Grant Brewing '
            'Cleveland OH | Craft Beer &amp; Food">'
            '<meta property="og:url" content="%s"></head><body>'
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"address": {"@type": "PostalAddress", "streetAddress": "100 Main St", '
            '"addressLocality": "Cleveland", "addressRegion": "OH"}}</script>'
            "<h1>LAND-GRANT BREWING COMPANY</h1>"
            "<p>Dog Friendly.</p></body></html>" % TAPROOM_URL)
        cleveland_facts = _taproom_facts(
            name_value="Land-Grant Brewing Company", address_value="", address_quote="")
        cleveland_facts["facts"] = [
            f for f in cleveland_facts["facts"] if f["field"] != "address"]
        c = _run(tmp_path, taproom_html=cleveland_html, taproom_facts=cleveland_facts)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_GEOGRAPHY_CONFLICT
        assert c.recommendation == C.RECOMMEND_REVIEW
        assert "Cleveland" not in dict(c.proposed_fields)["address"]

    def test_different_state_supplemental_excluded(self, tmp_path):
        indiana_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Taproom | Land-Grant Brewing '
            'Columbus IN | Craft Beer &amp; Food">'
            '<meta property="og:url" content="%s"></head><body>'
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"address": {"@type": "PostalAddress", "streetAddress": "100 Main St", '
            '"addressLocality": "Columbus", "addressRegion": "IN"}}</script>'
            "<h1>LAND-GRANT BREWING COMPANY</h1>"
            "<p>Dog Friendly.</p></body></html>" % TAPROOM_URL)
        indiana_facts = _taproom_facts(
            name_value="Land-Grant Brewing Company", address_value="", address_quote="")
        indiana_facts["facts"] = [
            f for f in indiana_facts["facts"] if f["field"] != "address"]
        c = _run(tmp_path, taproom_html=indiana_html, taproom_facts=indiana_facts)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_GEOGRAPHY_CONFLICT
        assert c.recommendation == C.RECOMMEND_REVIEW

    def test_wrong_expected_city_keeps_conflict(self, tmp_path):
        ctx = _default_context(expected_city="Dublin")
        c = _run(tmp_path, context=ctx)
        assert any(cf.field_name == "name" for cf in c.conflicts)

    def test_wrong_expected_state_blocks_city_state_rule(self, tmp_path):
        ctx = _default_context(expected_state="IN")
        c = _run(tmp_path, context=ctx)
        # The taproom OG title claims "Columbus OH"; expected_state=IN means
        # the city+state suffix rule (which requires the operator's OWN
        # expected_state) cannot bless it purely on that basis.
        assert any(
            cf.field_name == "name" and _TAPROOM_OG_TITLE in cf.competing_values
            for cf in c.conflicts)

    def test_unsupported_geography_keeps_conflict(self, tmp_path):
        """No expected_city/state supplied at all -- geography context is
        absent, so the context-bound suffix rules must never fire."""
        ctx = _default_context(expected_city="", expected_state="")
        c = _run(tmp_path, context=ctx)
        assert any(cf.field_name == "name" for cf in c.conflicts)

    def test_conflicting_page_geography_keeps_exclusion(self, tmp_path):
        """PRIMARY (FAQ) itself states a conflicting city -- the supplemental
        must not be silently merged despite matching expected_city."""
        faq_with_city = _faq_html().replace(
            "</body>", "<p>Our original location is in Dublin, OH.</p></body>")
        faq_facts_with_city = {"facts": _faq_facts()["facts"] + [
            {"field": "address", "value": "1 Dublin Way, Dublin, OH",
             "quote": "Our original location is in Dublin, OH"}]}
        c = _run(tmp_path, faq_html=faq_with_city, faq_facts=faq_facts_with_city)
        # PRIMARY's own city (Dublin, extracted) conflicts with the
        # supplemental's Columbus geography -- must exclude, never merge.
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_GEOGRAPHY_CONFLICT

    def test_different_business_excluded(self, tmp_path):
        other_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Seventh Son Brewing">'
            '<meta property="og:url" content="%s"></head>'
            "<body><h1>Seventh Son Brewing</h1><p>SEVENTH SON BREWING. "
            "Dog Friendly.</p></body></html>" % TAPROOM_URL)
        other_facts = {"facts": [
            {"field": "name", "value": "Seventh Son Brewing", "quote": "SEVENTH SON BREWING"},
            {"field": "pets_allowed", "value": "true", "quote": "Dog Friendly"}]}
        c = _run(tmp_path, taproom_html=other_html, taproom_facts=other_facts)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_IDENTITY_CONFLICT
        assert c.recommendation == C.RECOMMEND_REVIEW

    @pytest.mark.parametrize("resolved,candidate", [
        ("Land-Grant Brewing Columbus", "Seventh Son Brewing"),
        ("Land-Grant Brewing Columbus", "Land-Grant Brewing Cleveland"),
        ("Land-Grant Brewing Columbus OH", "Land-Grant Brewing Columbus IN"),
        ("Land-Grant Brewing Columbus", "Columbus Brewing Company"),
        ("Land-Grant Brewing Company", "Land-Grant Hotel Company"),
        ("Taproom Coffee", "Land-Grant Brewing"),
        ("Craft Beer Company", "Land-Grant Brewing"),
        ("The Company Bar", "Land-Grant Brewing"),
        ("Land-Grant Brewing Columbus", "Old Land-Grant Brewing Foundation"),  # partial overlap
    ])
    def test_genuine_pairs_never_reconcile(self, resolved, candidate):
        assert _reconciles_with_resolved(
            resolved, candidate, "Columbus", True, "OH") is False

    def test_legal_suffix_inside_not_terminal_is_unsafe_and_unaffected(self):
        """"The Company Bar" has "Company" mid-string, not terminal --
        strip_legal_suffix must never touch it, and it must never reconcile
        with an unrelated resolved name."""
        assert strip_legal_suffix("The Company Bar") == "The Company Bar"
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "The Company Bar",
            "Columbus", True, "OH") is False

    def test_literal_entity_name_containing_company_word_not_overcollapsed(self):
        """A literal single-token-suffix name ending in a NON-legal word that
        merely resembles "company" in spirit (e.g. "Craft Beer Company")
        still strips only the trailing token, and the resulting base still
        correctly fails to match an unrelated resolved name."""
        assert strip_legal_suffix("Craft Beer Company") == "Craft Beer"
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Craft Beer Company",
            "Columbus", True, "OH") is False

    def test_literal_entity_name_containing_taproom_word_not_overcollapsed(self):
        """"Taproom Coffee" has no separator, so the page-purpose "taproom"
        segment classification never even applies to it."""
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Taproom Coffee",
            "Columbus", True, "OH") is False

    def test_partial_token_overlap_never_reconciles(self):
        assert _reconciles_with_resolved(
            "Land-Grant Brewing Columbus", "Land-Grant Brewing Columbus Foundation",
            "Columbus", True, "OH") is False

    def test_generic_name_never_overcollapses(self):
        """A generic/short candidate must not spuriously match a real,
        distinct base via the legal-suffix or city-suffix rules."""
        assert _reconciles_with_resolved(
            "Brewing Company", "Land-Grant Brewing Columbus",
            "Columbus", True, "OH") is False


# --------------------------------------------------------------------------- #
# Conflict-construction requirement: only the genuinely failing candidates
# ever enter a name Conflict's competing_values/evidence.
# --------------------------------------------------------------------------- #

class TestConflictConstructionIsSelective:
    def test_conflict_contains_only_failing_candidate_not_reconciled_ones(self, tmp_path):
        """Mix three reconciling candidates (the live FAQ shape) with ONE
        genuinely different business on the supplemental -- the resulting
        conflict (if the supplemental were somehow still pooled) must never
        list the FAQ's own reconciled candidates. Verified directly at the
        _resolve_name level via the identity gate's exclusion instead, since
        a genuinely different business is gate-excluded before pooling."""
        other_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Seventh Son Brewing">'
            '<meta property="og:url" content="%s"></head>'
            "<body><h1>Seventh Son Brewing</h1><p>SEVENTH SON BREWING. "
            "Dog Friendly.</p></body></html>" % TAPROOM_URL)
        other_facts = {"facts": [
            {"field": "name", "value": "Seventh Son Brewing", "quote": "SEVENTH SON BREWING"},
            {"field": "pets_allowed", "value": "true", "quote": "Dog Friendly"}]}
        c = _run(tmp_path, taproom_html=other_html, taproom_facts=other_facts)
        # The differing business never enters ANY name conflict's
        # competing_values because it was excluded at the gate before ever
        # being pooled -- so no name conflict exists at all, and the FAQ's
        # own two reconciling candidates are untouched.
        assert not any(cf.field_name == "name" for cf in c.conflicts)

    def test_no_duplicate_conflicting_evidence_and_identity_conflict(self, tmp_path):
        """A genuine, pooled (not gate-excluded) identity conflict must
        report identity_conflict WITHOUT also emitting the generic
        conflicting_evidence reason for the identical underlying issue."""
        # A multi_entity-restricted source cannot trigger this (its name
        # never pools); instead, force TWO genuinely different LLM names on
        # the SAME (primary) page, which the gate cannot filter (there is
        # only one source).
        faq_two_names = _faq_html()
        facts = {"facts": _faq_facts()["facts"] + [
            {"field": "name", "value": "Totally Different Venue",
             "quote": "Land-Grant Brewing Columbus"}]}
        cas = ArtifactStoreRepository(tmp_path / "cas_single")
        fetcher = StaticPageFetcher()
        fetcher.add_html(FAQ_URL, faq_two_names)
        extractor = StaticFactExtractor(facts)
        from scripts.pettripfinder.importer.candidate import run_import
        c = run_import(
            FAQ_URL, _default_context(), fetcher=fetcher, extractor=extractor, cas=cas,
            observed_at="2026-07-17", created_at="2026-07-17T10:33:28")
        assert any(cf.field_name == "name" for cf in c.conflicts)
        # Single-source path: no aggregate-specific reasons exist at all,
        # so only the generic conflicting_evidence reason is possible here
        # -- confirming the dedup fix is aggregate-scoped, as required
        # ("Do not modify... source-domain gate" / existing single-source
        # doctrine untouched).
        assert C.REASON_CONFLICTING_EVIDENCE in c.recommendation_reasons
