"""AES-DATA-003F -- entity-name title-suffix canonicalization (Task 6/7).
Hardens ``normalize.names_compatible`` against official page titles that
combine a clean business name with a marketing tagline (delimiter-
separated), without collapsing genuinely different businesses/locations.
Static, pure-function tests only -- no network, no live provider calls."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.importer.normalize import (
    brand_split,
    clean_entity_name,
    names_compatible,
)


# --------------------------------------------------------------------------- #
# 9-11. Marketing-suffix removal across delimiter variants.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("clean,title", [
    ("Homedog Resort & Daycare", "Homedog Resort & Daycare | Dog Boarding & Dog Daycare"),
    ("Designer Paws Salon", "Designer Paws Salon | Dog Grooming, Cat Grooming & More"),
    ("Fangs & Fur", "Fangs & Fur | Natural Pet Food in Columbus"),
])
def test_9_pipe_marketing_suffix_removed_safely(clean, title):
    assert names_compatible(clean, title) is True


@pytest.mark.parametrize("sep", ["–", "—"])   # en dash, em dash
def test_10_dash_and_em_dash_variants(sep):
    title = "Fangs & Fur %s Natural Pet Food in Columbus" % sep
    assert names_compatible("Fangs & Fur", title) is True


def test_11_colon_variant():
    title = "Fangs & Fur: Natural Pet Food in Columbus"
    assert names_compatible("Fangs & Fur", title) is True


def test_middot_delimiter_recognized():
    title = "Fangs & Fur · Natural Pet Food in Columbus"
    segs = brand_split(title)
    assert segs == ["Fangs & Fur", "Natural Pet Food in Columbus"]
    assert names_compatible("Fangs & Fur", title) is True


# --------------------------------------------------------------------------- #
# 12-13. Distinct locations/entities must never collapse.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("a,b", [
    ("Pet Palace Columbus", "Pet Palace Hilliard"),
    ("Columbus Pet Resort", "Dublin Pet Resort"),
])
def test_12_distinct_locations_remain_distinct(a, b):
    assert names_compatible(a, b) is False


@pytest.mark.parametrize("a,b", [
    ("Northstar Veterinary Hospital", "Northstar Emergency Veterinary Hospital"),
    ("Healthy Pets", "Healthy Pets Pharmacy"),
])
def test_13_distinct_entities_remain_distinct(a, b):
    assert names_compatible(a, b) is False


# --------------------------------------------------------------------------- #
# 14. Title-only weak identity stays conservative: a title whose LEADING
# segment does not match the resolved/clean name never reconciles merely
# because SOME segment resembles it.
# --------------------------------------------------------------------------- #

def test_14_non_leading_segment_match_stays_conservative():
    # "Fangs & Fur" appears, but NOT as the leading segment -- this must not
    # reconcile (a trailing mention is not the same as the title BEGINNING
    # with the trusted name, per Task 7). "Weekend Roundup" is deliberately
    # not a recognized site-brand/page-purpose boilerplate word either, so
    # this isolates the NEW leading-segment rule from the pre-existing
    # boilerplate-segment path.
    title = "Weekend Roundup | Fangs & Fur"
    assert names_compatible("Fangs & Fur", title) is False


def test_14b_leading_segment_must_match_exactly_not_fuzzily():
    # A leading segment that merely CONTAINS the trusted name is not an
    # exact match -- never collapses via fuzzy substring reasoning.
    title = "Fangs & Fur Columbus | Natural Pet Food"
    assert names_compatible("Fangs & Fur", title) is False


# --------------------------------------------------------------------------- #
# Symmetry and idempotence.
# --------------------------------------------------------------------------- #

def test_reconciliation_is_symmetric():
    a, b = "Homedog Resort & Daycare", "Homedog Resort & Daycare | Dog Boarding & Dog Daycare"
    assert names_compatible(a, b) == names_compatible(b, a) is True


def test_clean_entity_name_unaffected_by_new_rule():
    # clean_entity_name's own boilerplate-keyword behavior is untouched --
    # the new leading-segment rule only extends names_compatible.
    assert clean_entity_name("Scioto Audubon - Metro Parks") == "Scioto Audubon"


def test_no_delimiter_no_effect():
    # A plain undelimited name never engages the new rule at all.
    assert names_compatible("Fangs & Fur", "Fangs and Fur Pet Supply") is False
