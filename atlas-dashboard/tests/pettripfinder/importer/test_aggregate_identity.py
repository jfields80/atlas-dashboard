"""AES-DATA-002B -- deterministic identity gate: same-registrable-domain,
entity-name reconciliation, and geography agreement. A supplemental that
fails any gate is EXCLUDED (its SourceRecord stays visible with an
excluded_reason) -- never silently merged, never fuzzy-matched. No network."""

from __future__ import annotations

from pettripfinder.importer._aggregate_helpers import (
    CONTACT_URL,
    FAQ_URL,
    build_fetcher_extractor,
    contact_facts,
    contact_html,
    default_context,
    faq_facts,
    faq_html,
    make_cas,
)

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import

_FAQ_MARKER = "Beer Garden operations are weather dependent"
_CONTACT_MARKER = "Call the taproom at"


def _run(pages, facts_by_marker, ctx, urls=None):
    fetcher, extractor = build_fetcher_extractor(pages, facts_by_marker)
    urls = urls or [u for u, _h in pages]
    return lambda tmp_path: run_multi_import(
        urls, ctx, fetcher=fetcher, extractor=extractor, cas=make_cas(tmp_path),
        observed_at="2026-07-17", created_at="1970-01-01T00:00:00")


class TestValidMerge:
    def test_matching_entity_included_no_exclusion(self, tmp_path):
        """Baseline: the motivating FAQ + contact pair passes every gate."""
        run = _run(
            [(FAQ_URL, faq_html()), (CONTACT_URL, contact_html())],
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()},
            default_context())
        c = run(tmp_path)
        assert not any(s.excluded_reason for s in c.sources)
        assert c.recommendation == C.RECOMMEND_READY


class TestGeographyGate:
    def test_different_city_excluded(self, tmp_path):
        """Same brand, different city: identical/compatible names on both
        pages so ONLY the geography axis differs -- the supplemental's own
        structured city contradicts the operator's expected_city even
        though the FAQ (PRIMARY) states no city at all."""
        cleveland_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Land-Grant Brewing">'
            '<meta property="og:url" content="%s">'
            "</head><body>"
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"name": "Land-Grant Brewing", '
            '"address": {"@type": "PostalAddress", "streetAddress": "500 Main St", '
            '"addressLocality": "Cleveland", "addressRegion": "OH", "postalCode": "44101"}}'
            "</script><h1>Land-Grant Brewing</h1>"
            "<p>Visit our Cleveland taproom at 500 Main St.</p>"
            "</body></html>" % CONTACT_URL)
        run = _run(
            [(FAQ_URL, faq_html()), (CONTACT_URL, cleveland_html)],
            {_FAQ_MARKER: faq_facts(), "Cleveland": {"facts": []}},
            default_context())
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_GEOGRAPHY_CONFLICT
        assert supp.usable is True     # visible, not silently dropped
        assert C.REASON_GEOGRAPHY_CONFLICT in c.recommendation_reasons
        assert C.REASON_INCOMPLETE_SOURCE_SET in c.recommendation_reasons
        assert c.recommendation == C.RECOMMEND_REVIEW
        # No Cleveland fields merged.
        p = dict(c.proposed_fields)
        assert "Cleveland" not in p["address"]
        assert p["city"] != "Cleveland"

    def test_different_street_same_city_not_silently_merged(self, tmp_path):
        """Two branches in the same city, both fetched: PRIMARY (the FAQ
        page) states no address at all, so the pairwise PRIMARY-vs-
        supplemental gate has nothing to compare and passes both contact
        pages through -- but the residual supplemental-vs-supplemental
        disagreement is still caught at merge time (Task 9): neither street
        is silently picked, the address is left unpublished, and the
        candidate goes to REVIEW with geography_conflict."""
        branch_url = "https://landgrantbrewing.com/branch/"
        branch_html = contact_html(street="9999 Other Ave", city="Columbus",
                                   state="OH", postal="43214", phone="614-000-1111")
        run = _run(
            [(FAQ_URL, faq_html()), (CONTACT_URL, contact_html()), (branch_url, branch_html)],
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()},
            default_context(), urls=[FAQ_URL, CONTACT_URL, branch_url])
        c = run(tmp_path)
        # Neither contact page is gate-excluded (PRIMARY has no address to
        # compare against); the conflict surfaces at the merge layer instead.
        assert not any(s.excluded_reason for s in c.sources)
        p = dict(c.proposed_fields)
        assert p["address"] == ""
        assert "9999 Other Ave" not in p["address"]
        assert "424 W Town St" not in p["address"]
        assert any(cf.field_name == "address" for cf in c.conflicts)
        assert C.REASON_GEOGRAPHY_CONFLICT in c.recommendation_reasons
        assert c.recommendation == C.RECOMMEND_REVIEW


class TestIdentityGate:
    def test_different_business_same_domain_excluded(self, tmp_path):
        """A genuinely different business on the same domain must never
        merge -- caught by name reconciliation, never fuzzy matching."""
        other_biz_html = (
            "<!doctype html><html><head>"
            '<meta property="og:title" content="Seventh Son Brewing">'
            '<meta property="og:url" content="%s">'
            "</head><body><h1>Seventh Son Brewing</h1>"
            "<p>A completely different taproom.</p></body></html>"
            % "https://landgrantbrewing.com/other-tenant/")
        run = _run(
            [(FAQ_URL, faq_html()),
             ("https://landgrantbrewing.com/other-tenant/", other_biz_html)],
            {_FAQ_MARKER: faq_facts(), "completely different taproom": {"facts": []}},
            default_context(),
            urls=[FAQ_URL, "https://landgrantbrewing.com/other-tenant/"])
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_IDENTITY_CONFLICT
        assert C.REASON_IDENTITY_CONFLICT in c.recommendation_reasons
        assert c.recommendation == C.RECOMMEND_REVIEW

    def test_operator_hint_reconciles_otherwise_ambiguous_pair(self, tmp_path):
        """A supported operator candidate_name hint reconciling with BOTH
        pages' text passes the gate even when the pages' own titles alone
        would not have obviously agreed."""
        vague_contact_html = (
            "<!doctype html><html><head>"
            '<meta property="og:url" content="%s">'
            "</head><body>"
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": "Restaurant", '
            '"telephone": "614-586-0413", '
            '"address": {"@type": "PostalAddress", "streetAddress": "424 W Town St", '
            '"addressLocality": "Columbus", "addressRegion": "OH", "postalCode": "43215"}}'
            "</script>"
            "<p>Land-Grant Brewing Columbus is located at 424 W Town St. "
            "Call the taproom at 614-586-0413.</p>"
            "</body></html>" % CONTACT_URL)
        run = _run(
            [(FAQ_URL, faq_html()), (CONTACT_URL, vague_contact_html)],
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()},
            default_context(candidate_name="Land-Grant Brewing Columbus"))
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == ""
        assert dict(c.proposed_fields)["address"] == "424 W Town St"


class TestDomainAndRelationshipGate:
    def test_cross_registrable_domain_excluded(self, tmp_path):
        """A different registrable domain never merges in V1, even when it
        looks official (matching name/branding)."""
        cross_domain_url = "https://landgrantbrewingcolumbus.example.test/contact/"
        cross_html = contact_html(url=cross_domain_url)
        run = _run(
            [(FAQ_URL, faq_html()), (cross_domain_url, cross_html)],
            {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()},
            default_context(), urls=[FAQ_URL, cross_domain_url])
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        assert supp.excluded_reason == C.REASON_DIFFERENT_REGISTRABLE_DOMAIN
        assert C.REASON_INCOMPLETE_SOURCE_SET in c.recommendation_reasons
        assert c.recommendation == C.RECOMMEND_REVIEW
        assert dict(c.proposed_fields)["address"] == ""

    def test_third_party_supplemental_excluded(self, tmp_path):
        yelp_url = "https://www.yelp.com/biz/land-grant-brewing-columbus"
        yelp_html = (
            '<!doctype html><html><body><h1>Land-Grant Brewing - Yelp Reviews</h1>'
            "</body></html>")
        run = _run(
            [(FAQ_URL, faq_html()), (yelp_url, yelp_html)],
            {_FAQ_MARKER: faq_facts(), "Yelp Reviews": {"facts": []}},
            default_context(), urls=[FAQ_URL, yelp_url])
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        # Excluded via the known third-party host marker regardless of what
        # the (correctly primary-scoped) operator relationship hint says.
        assert supp.excluded_reason == C.REASON_THIRD_PARTY_SOURCE
        assert C.REASON_INCOMPLETE_SOURCE_SET in c.recommendation_reasons
        assert c.recommendation == C.RECOMMEND_REVIEW


class TestMultiEntitySource:
    def test_multi_entity_contributes_policy_not_identity(self, tmp_path):
        """A page whose structured data names multiple businesses may still
        contribute pet-policy facts, but never identity/geography fields,
        and must not make the aggregate READY on its own."""
        multi_html = (
            "<!doctype html><html><head>"
            '<meta property="og:url" content="%s">'
            "</head><body>"
            '<script type="application/ld+json">[{"@type": "Restaurant", '
            '"name": "Land-Grant Brewing", '
            '"address": {"streetAddress": "1 Wrong Ave", "addressLocality": "Nowhere", '
            '"addressRegion": "OH"}}, {"@type": "Restaurant", "name": "Some Other Venue"}]'
            "</script>"
            "<p>Additional dogs are welcome on the shared patio here too.</p>"
            "</body></html>" % "https://landgrantbrewing.com/food-hall/")
        run = _run(
            [(FAQ_URL, faq_html()), ("https://landgrantbrewing.com/food-hall/", multi_html)],
            {_FAQ_MARKER: faq_facts(),
             "shared patio": {"facts": [
                 {"field": "water_or_treats", "value": "true",
                  "quote": "dogs are welcome on the shared patio"}]}},
            default_context(), urls=[FAQ_URL, "https://landgrantbrewing.com/food-hall/"])
        c = run(tmp_path)
        supp = next(s for s in c.sources if s.role == C.SOURCE_ROLE_SUPPLEMENTAL)
        # Included (not gate-excluded)...
        assert supp.excluded_reason == ""
        # ...but its geography never leaks into the merged output.
        p = dict(c.proposed_fields)
        assert "Wrong Ave" not in p["address"]
        assert p["city"] != "Nowhere"
        assert C.REASON_MULTI_ENTITY in c.recommendation_reasons
        assert c.recommendation != C.RECOMMEND_READY
