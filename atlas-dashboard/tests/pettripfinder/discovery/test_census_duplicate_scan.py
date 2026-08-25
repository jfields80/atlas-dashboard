"""PTF-LOUISVILLE-FOUNDER-REVIEW-004 -- finding two identities for one building
before publication rather than after.

The scan's value is that it does NOT decide. Sharing an address is evidence, not
a verdict: Louisville has a dual-brand building where two hotels legitimately
share one street address, and a two-tower hotel where one business legitimately
answers to two names. Both come out of here as groups for a person to read.
"""

from __future__ import annotations

from scripts.pettripfinder.discovery import census_duplicate_scan as DS


def row(key, **over):
    base = {"identity_key": key, "canonical_name": key.title(), "address": "",
            "postal_code": "", "phone": "", "official_url": "", "slug": ""}
    base.update(over)
    return base


class TestSignals:
    def test_two_identities_at_one_address_are_grouped(self):
        groups = DS.scan([row("hampton", address="1150 Forest Bridge Rd",
                              postal_code="40223"),
                          row("home2", address="1150 Forest Bridge Road",
                              postal_code="40223")])
        assert [g["signal"] for g in groups] == ["STREET_AND_POSTAL_CODE"]
        assert groups[0]["identity_keys"] == ["hampton", "home2"]

    def test_two_identities_on_one_url_are_grouped(self):
        groups = DS.scan([row("a", official_url="https://x/y/"),
                          row("b", official_url="https://x/y")])
        assert groups[0]["signal"] == "SOURCE_URL"
        assert "another building's policy" in groups[0]["why_it_matters"]

    def test_two_identities_on_one_telephone_line_are_grouped(self):
        groups = DS.scan([row("a", phone="(502) 585-3200"),
                          row("b", phone="+1 502 585 3200")])
        assert groups[0]["signal"] == "TELEPHONE"

    def test_an_empty_signal_groups_nothing(self):
        """The bug every one of these scans is written around: bucketing on a
        field most rows leave blank marries every blank row to every other."""
        assert DS.scan([row("a"), row("b"), row("c")]) == []

    def test_a_street_with_no_postal_code_is_not_a_key(self):
        assert DS.scan([row("a", address="1 Main St"),
                        row("b", address="1 Main St")]) == []


class TestReporting:
    def test_a_group_holding_a_candidate_is_reported_first(self):
        rows = [row("a", phone="5025853200"), row("b", phone="5025853200"),
                row("c", address="1 Main St", postal_code="40202"),
                row("d", address="1 Main St", postal_code="40202")]
        groups = DS.scan(rows, candidates={"c"})
        assert groups[0]["includes_a_review_candidate"] is True
        assert groups[0]["identity_keys"] == ["c", "d"]

    def test_every_group_says_which_signal_grouped_it_and_why(self):
        groups = DS.scan([row("a", slug="x"), row("b", slug="x")])
        assert groups[0]["signal"] == "SLUG"
        assert groups[0]["why_it_matters"]
        assert groups[0]["size"] == 2

    def test_nothing_is_merged_or_resolved(self):
        groups = DS.scan([row("a", slug="x"), row("b", slug="x")])
        assert set(groups[0]) == {"signal", "value", "identity_keys", "size",
                                  "includes_a_review_candidate",
                                  "why_it_matters"}
