# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-WEIGHT-SEMANTICS-RULING-023.

"under 75 lbs" and "up to 75 lbs" are different promises. A guest arriving with
a 75 lb dog is welcome under one and turned away under the other, and founder
decision 1 published both as ``lte`` because it only ever asked whether the
wording was a ceiling at all. This ruling asks the narrower question the schema
actually needs -- WHICH comparison -- and answers it only from wording the
source states.

THE FOURTH CASE IS THE POINT. A source that states a number and no comparison
gets its weight field WITHHELD. Publishing it as ``lte`` tells a guest at
exactly that weight they are welcome; publishing it as ``lt`` tells them the
opposite; and there is no third value that means "we do not know". So the field
is withheld and the withholding says why, which is a decision a reviewer can
re-adjudicate when a better capture arrives.

WHAT MUST NOT MOVE. Founder decision 1 is still the rule that four published
markets were built under, so ``_MAXIMAL_RE`` keeps every phrase it had. Only
"must not weigh more than" is added, and no committed package outside Grand
Rapids contains that phrasing -- so no existing market's semantics can shift.
The new reading is a separate opt-in a caller must name, exactly as decision 1
is.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import market_policy_package_cli as PP  # noqa: E402
from scripts.pettripfinder.contracts import enums                  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"
PACKAGE = LP / ("hotel_policy_facts_%s.json" % MARKET)


def _project(quote, value=75.0, extra=None):
    source = {"pets_allowed": True,
              "weight_limit": {"value": value, "unit": "lb"}}
    source.update(extra or {})
    evidence = [{"field_refs": ["weight_limit"], "quote": quote}] if quote else []
    facts, notes = PP.project_facts(source, evidence,
                                    weight_comparison_from_source=True)
    return facts.get("weight_limit"), notes


# --------------------------------------------------------------------------- #
# The founder's stated cases
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("quote,value,operator", [
    ("up to 75 lb", 75.0, "lte"),
    ("maximum 75 lb", 75.0, "lte"),
    ("Max weight 75 lbs", 75.0, "lte"),
    ("no more than 75 lbs", 75.0, "lte"),
    ("must not weigh more than 100 lbs", 100.0, "lte"),
    ("under 75 lb", 75.0, "lt"),
    ("less than 75 lbs", 75.0, "lt"),
])
def test_the_comparison_the_source_states_is_the_one_published(quote, value,
                                                               operator):
    node, _notes = _project(quote, value)
    assert node is not None, quote
    assert node["operator"] == operator
    assert node["scope"] == enums.WEIGHT_SCOPE_PER_PET
    assert node["value"] == value


def test_a_bare_number_invents_no_operator():
    """The whole reason this ruling exists rather than a wider default."""
    node, notes = _project("75 lb")
    assert node is None
    assert any("WITHHELD" in n for n in notes)


def test_a_number_with_no_quote_at_all_invents_no_operator():
    node, notes = _project("")
    assert node is None
    assert any("no quote cites the weight limit" in n for n in notes)


def test_a_source_stating_both_comparisons_is_refused():
    """This layer does not choose between two things the source says."""
    node, notes = _project("up to 75 lbs, under 80 lbs combined per stay")
    assert node is None


# --------------------------------------------------------------------------- #
# The combined-weight safeguard, preserved
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("quote", [
    "combined weight of 100 lbs",
    "total weight of 100 lbs for all pets",
    "both pets together must not weigh more than 100 lbs",
])
def test_a_shared_weight_is_never_republished_as_per_pet(quote):
    node, _notes = _project(quote, 100.0)
    assert node is None, "a combined weight is a different fact from a per-pet one"


def test_a_separate_combined_limit_on_the_record_also_refuses():
    node, _notes = _project("maximum 75 lbs",
                            extra={"combined_weight_limit": {"value": 120.0}})
    assert node is None


def test_the_withholding_names_the_reason_and_can_be_re_adjudicated():
    source = {"weight_limit": {"value": 75.0, "unit": "lb"}}
    decision = PP.weight_withholding(source, ["Pet weight 75"], ["ref-1"])
    assert decision["reason_code"] == enums.SOURCE_AMBIGUOUS
    assert "RULING-023" in decision["reason"]
    assert decision["evidence_refs"] == ["ref-1"]

    combined = PP.weight_withholding(
        {"weight_limit": {"value": 100.0, "unit": "lb"}},
        ["combined weight of 100 lbs"], ["ref-2"])
    assert combined["reason_code"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_row_the_ruling_can_read_is_not_withheld():
    assert PP.weight_withholding(
        {"weight_limit": {"value": 75.0, "unit": "lb"}},
        ["up to 75 lbs"], ["ref"]) is None
    assert PP.weight_withholding(
        {"weight_limit": {"value": 75.0, "unit": "lb",
                          "operator": "lte", "scope": "per_pet"}},
        [], []) is None


# --------------------------------------------------------------------------- #
# What must not move
# --------------------------------------------------------------------------- #

def test_founder_decision_one_still_reads_every_phrase_it_read_before():
    """Four markets are published under it. Its list may gain a phrase and
    must never lose one."""
    for phrase in ("max", "maximum", "up to", "under", "less than",
                   "no more than", "or less", "not exceed", "weight limit",
                   "limit of"):
        assert PP._MAXIMAL_RE.search("weight %s 50 lbs" % phrase), phrase
    assert PP._MAXIMAL_RE.search("must not weigh more than 100 lbs")


def test_the_ceiling_list_deliberately_excludes_the_strict_forms():
    """Their absence IS the distinction this ruling preserves."""
    assert not PP._CEILING_RE.search("under 75 lbs")
    assert not PP._CEILING_RE.search("less than 75 lbs")
    assert PP._STRICT_LESS_RE.search("under 75 lbs")
    assert PP._STRICT_LESS_RE.search("less than 75 lbs")


def test_the_new_reading_is_off_by_default():
    """A caller must name the ruling, exactly as decision 1 requires."""
    source = {"pets_allowed": True, "weight_limit": {"value": 75.0, "unit": "lb"}}
    evidence = [{"field_refs": ["weight_limit"], "quote": "up to 75 lbs"}]
    facts, _notes = PP.project_facts(source, evidence)
    assert facts["weight_limit"] == {"value": 75.0, "unit": "lb"}, (
        "the strict default emits neither an operator nor a scope")


def test_the_new_reading_takes_precedence_over_decision_one():
    """A caller naming both gets the more specific answer, which is the only
    one that can tell lt from lte."""
    source = {"pets_allowed": True, "weight_limit": {"value": 75.0, "unit": "lb"}}
    evidence = [{"field_refs": ["weight_limit"], "quote": "pets under 75 lbs"}]
    facts, _notes = PP.project_facts(source, evidence, normalize_weight=True,
                                     weight_comparison_from_source=True)
    assert facts["weight_limit"]["operator"] == "lt", (
        "decision 1 would have flattened this to lte")


def test_no_other_market_carries_the_newly_recognised_phrase():
    """The one way extending _MAXIMAL_RE could move a published market."""
    for path in sorted(LP.glob("hotel_policy_facts*.json")):
        if path.name == PACKAGE.name:
            continue
        # PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 published Baymont by Wyndham Indianapolis West, whose
        # own page states "Pets must not weigh more than 25 lbs each"; the phrase now
        # legitimately appears in that package as a cited quote. The guard this test
        # carries -- that extending _MAXIMAL_RE moved no OTHER market at 023 -- is
        # unchanged for every market published before it.
        if path.name == "hotel_policy_facts_indianapolis-in.json":
            continue
        text = path.read_text(encoding="utf-8").lower()
        assert "must not weigh more than" not in text, path.name


# --------------------------------------------------------------------------- #
# Grand Rapids, measured
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def package():
    assert PACKAGE.is_file()
    return json.loads(PACKAGE.read_text(encoding="utf-8"))


def test_the_market_measured_under_the_ruling(package):
    """24 lte, 1 lt, and the one withheld weight is a UNIT ambiguity the reader
    had already refused -- not something this ruling withheld."""
    operators = {}
    withheld = []
    for hotel in package["hotels"]:
        limit = hotel["facts"].get("weight_limit")
        if limit:
            operators[limit["operator"]] = operators.get(limit["operator"], 0) + 1
        if "weight_limit" in (hotel.get("withheld_fields") or {}):
            withheld.append(hotel["identity_key"])
    # 023 measured 24 lte and 1 lt over the 35 it published. Later promotions
    # add rows and the totals grow; what the RULING is answerable for is that
    # every operator it emits is one it read from a source, that lte and lt are
    # the only two, and that the unit ambiguity it refused stays refused.
    assert set(operators) <= {"lte", "lt"}
    assert operators.get("lte", 0) >= 24 and operators.get("lt", 0) >= 1
    assert "holiday inn express grand rapids sw" in withheld


def test_the_one_strict_row_publishes_lt(package):
    row = next(h for h in package["hotels"]
               if h["identity_key"] == "days inn by wyndham holland")
    assert row["facts"]["weight_limit"] == {
        "value": 75.0, "unit": "lb", "operator": "lt", "scope": "per_pet"}


def test_the_withheld_weight_is_a_unit_ambiguity_not_a_comparison_one():
    """It was withheld by the READER, before this ruling existed: the surface
    said "Pet weight limit: 75" and named no unit, and pounds and kilograms are
    different policies."""
    store = json.loads(
        (LP / "grand_rapids_holland_mi_observation_store_022.json")
        .read_text(encoding="utf-8"))
    record = next(r for r in store["records"]
                  if r["identity_key"] == "holiday inn express grand rapids sw")
    assert record["withheld_fields"]["weight_limit"] == enums.SOURCE_AMBIGUOUS
    assert record["observation"]["extraction"].get("weight_limit") is None
    detail = " ".join(str(f.get("detail") or "")
                      for f in record["observation"].get("flags") or ())
    assert "names no unit" in detail


def test_this_ruling_withheld_nothing_in_this_market():
    """Every one of the 25 weight rows states a comparison, so the fourth case
    never fired here. Reporting it as if it had would be inventing a finding."""
    authority = json.loads(
        (LP / "grand_rapids_holland_mi_proposed_authority_022.json")
        .read_text(encoding="utf-8"))
    withheld = 0
    for row in authority["pet_friendly"]:
        quotes = [str(e.get("quote", "")) for e in (row.get("evidence") or ())
                  if "weight_limit" in (e.get("field_refs") or ())]
        if PP.weight_withholding(row.get("facts") or {}, quotes, ["ref"]):
            withheld += 1
    assert withheld == 0


def test_every_record_passes_the_schema(package):
    assert package["refusals"] == []
    assert package["count"] == len(package["hotels"])
