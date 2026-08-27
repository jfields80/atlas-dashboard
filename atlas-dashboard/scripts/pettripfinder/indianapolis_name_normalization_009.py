# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009 -- replay 25 paid lookups, twice.

008 spent 25 Google Places requests and bound 9. Thirteen of the sixteen misses
still came back with a real property page, and eleven of those were plainly the
intended hotel under the brand's current marketing name. The rule was not wrong
to refuse them -- it was comparing PRESENTATION and calling it identity.

This module replays those 25 saved responses through the old binder and the new
one and reports the difference, row by row. IT CALLS NOTHING. Every payload is
already on disk and already paid for; the discovery ledger suppresses all 25
from ever being bought again.

WHAT WOULD MAKE THIS A FAILURE RATHER THAN AN IMPROVEMENT
----------------------------------------------------------
Four rows must still refuse to bind, and they are the reason the work is worth
doing carefully rather than quickly:

  aloft                  a bare brand word. Places returned the real Aloft
                         Indianapolis Downtown with a genuine Marriott page.
                         A brand is not a building.
  ashley motel           the place carries no website at all.
  cambria westfield      Places offered a Hampton Inn.
  hampton inn carmel     Places offered the Homewood Suites -- the dual-brand
                         confusion the whole ledger doctrine is written against.

A fifth is worth watching for the same reason and is reported beside them:
"Best Western Plus Indianapolis North at BROAD RIPPLE" against Places'
"...North at PYRAMIDS". Same brand, same city, same compass word, different
building.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import market_routing as MR       # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC   # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RUN_DOC = "indianapolis_in_places_qualification_008.json"
SCHEMA = "ptf-name-normalization-replay/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009"
MARKET = "indianapolis-in"

#: Must not bind, before or after. The first two are the committed controls;
#: the last two are wrong hotels Places actually offered.
PROTECTED = OrderedDict((
    ("aloft", "a bare brand word; Places returned the real Aloft Indianapolis "
              "Downtown and a brand is still not a building"),
    ("ashley motel", "the place carries no website at all"),
    ("cambria hotel westfield indianapolis north",
     "Places offered a Hampton Inn -- a different brand and a different hotel"),
    ("hampton inn and suites indianapolis carmel",
     "Places offered the Homewood Suites -- the dual-brand confusion the "
     "ledger doctrine exists to prevent"),
))

#: Watched for the same reason, and reported: same brand, same compass word,
#: different building.
WATCHED = ("best western plus indianapolis north at broad ripple",)


def _row_for_bind(row: Dict) -> Dict:
    signals = row["binding_signals"]
    parts = row["query"].split(", ")
    return {"identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "address": parts[1] if len(parts) > 1 else "",
            "city": "Indianapolis", "state": "IN",
            "postal_code": signals["census_postal"],
            "phone": signals["census_phone"]}


def _observations(row: Dict) -> List[URC.Observation]:
    return [URC.Observation(provider=URC.GOOGLE_PLACES,
                            source="places:%s" % (x.get("place_id") or "?"),
                            name=x.get("name", ""), phone=x.get("phone", ""),
                            postal=_postal_of(x), url=x.get("website_uri", ""),
                            street=x.get("address", ""))
            for x in row.get("returned", [])]


def _postal_of(place: Dict) -> str:
    """The Places postal code, read back off the formatted address.

    008 kept the parsed postal only for the row it bound; the address line is
    the durable record for every returned place, and the five-digit group at
    its end is the postal code in every US formatted address Places emits.
    """
    tokens = (place.get("address") or "").replace(",", " ").split()
    for token in reversed(tokens):
        if len(token) == 5 and token.isdigit():
            return token
    return ""


def _bind(row: Dict, *, variants: bool) -> Tuple[str, str, str]:
    """``(binding, url, why)`` under one rule."""
    census = _row_for_bind(row)
    observations = _observations(row)

    def acceptable(observation) -> Tuple[bool, str]:
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        if MR.classify_url_shape(url) not in MR.ROUTABLE_SHAPES:
            return (False, "the website is a %s"
                    % MR.classify_url_shape(url))
        return URC.url_names_the_property(census["canonical_name"], url)

    rejected: List[Dict] = []
    observation, binding = URC.bind(census, observations,
                                    unambiguous_streets=None,
                                    acceptable=acceptable, rejected=rejected,
                                    presentation_variants=variants)
    if observation is None:
        why = rejected[0]["why"] if rejected else "no sanctioned key matched"
        return ("", "", why)
    return (binding, MR.normalize_source_url(observation.url), "")


def _rule_that_changed_it(census_name: str, places_name: str) -> str:
    """Which of the three transformations made these two names equal."""
    old_c, old_p = URC.normalise(census_name), URC.normalise(places_name)
    if old_c == old_p:
        return "none -- the names already matched"
    reasons = []
    if " by " in " %s " % old_p or " by " in " %s " % old_c:
        for operator in URC._OPERATOR_TOKENS:
            if ("by %s" % operator) in old_p or ("by %s" % operator) in old_c:
                reasons.append("dropped the operator token 'by %s'" % operator)
                break
    if "and" in old_c.split() or "and" in old_p.split():
        reasons.append("folded 'and' to match '&'")
    if "in" in old_p.split() or "in" in old_c.split():
        reasons.append("dropped the bare state code 'in'")
    for written, canonical in URC._CHAIN_PRESENTATION:
        if old_p.startswith(written) or old_c.startswith(written):
            reasons.append("chain re-presentation %r -> %r" % (written, canonical))
            break
    return "; ".join(reasons) or "no single rule -- still different"


def build() -> Dict:
    run = json.loads((LP / RUN_DOC).read_text(encoding="utf-8"))
    rows = [r for r in run["rows"] if r.get("requests_made")]

    detail: List[Dict] = []
    for row in rows:
        old_binding, old_url, old_why = _bind(row, variants=False)
        new_binding, new_url, new_why = _bind(row, variants=True)
        census_name = row["canonical_name"]
        matched = ""
        for place in row.get("returned", []):
            if new_url and MR.normalize_source_url(place.get("website_uri", "")) == new_url:
                matched = place.get("name", "")
                break
        if not matched and row.get("returned"):
            matched = row["returned"][0].get("name", "")

        detail.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("expected_binding_method", row["expected_binding_method"]),
            ("census_name", census_name),
            ("places_name", matched),
            ("old_normalized_census", URC.normalise(census_name)),
            ("old_normalized_places", URC.normalise(matched)),
            ("new_normalized_census", URC.presentation_key(census_name, state_code="IN")),
            ("new_normalized_places", URC.presentation_key(matched, state_code="IN")),
            ("old_decision", "BOUND" if old_binding else "UNBOUND"),
            ("new_decision", "BOUND" if new_binding else "UNBOUND"),
            ("changed", bool(new_binding) != bool(old_binding)),
            ("rule_that_changed_it",
             _rule_that_changed_it(census_name, matched)
             if (bool(new_binding) != bool(old_binding)) else ""),
            ("final_binding_method", new_binding or old_binding or ""),
            ("url", new_url or old_url),
            ("why_unbound", new_why),
            ("protected", row["identity_key"] in PROTECTED),
            ("watched", row["identity_key"] in WATCHED),
            ("identity_remains_safe",
             not (row["identity_key"] in PROTECTED and bool(new_binding))),
        )))

    def tally(pred):
        chosen = [d for d in detail if pred(d)]
        return OrderedDict((
            ("attempted", len(chosen)),
            ("old", sum(1 for d in chosen if d["old_decision"] == "BOUND")),
            ("new", sum(1 for d in chosen if d["new_decision"] == "BOUND")),
        ))

    protected_binds_new = [d["identity_key"] for d in detail
                           if d["protected"] and d["new_decision"] == "BOUND"]
    watched_binds_new = [d["identity_key"] for d in detail
                         if d["watched"] and d["new_decision"] == "BOUND"]
    newly = [d for d in detail if d["changed"] and d["new_decision"] == "BOUND"]
    lost = [d for d in detail if d["changed"] and d["new_decision"] == "UNBOUND"]

    np_stat = tally(lambda d: d["expected_binding_method"] == "NAME_AND_POSTAL_CODE")
    new_rate = np_stat["new"] / np_stat["attempted"] if np_stat["attempted"] else 0.0
    remaining = 118

    safe = (not protected_binds_new and not watched_binds_new and not lost)
    improved = np_stat["new"] > np_stat["old"]

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("replayed_from", RUN_DOC),
        ("rules", OrderedDict((
            ("operator_presentation_token",
             ["by %s" % o for o in URC._OPERATOR_TOKENS]),
            ("ampersand_and_the_word_and", True),
            ("bare_state_code", "IN"),
            ("chain_re_presentation", [list(p) for p in URC._CHAIN_PRESENTATION]),
            ("never_removed", ["airport", "downtown", "north", "south", "east",
                               "west", "northwest", "northeast", "southwest",
                               "southeast", "inn", "suites", "every locality",
                               "the city name itself"]),
            ("no_fuzzy_matching",
             "every comparison is token-sequence equality; no edit distance, no "
             "similarity score, no overlap threshold"),
            ("opt_in", "bind(presentation_variants=True); default OFF, so every "
                       "market that recovered its URLs under the old rule "
                       "recovers exactly the same ones today"),
        ))),
        ("totals", OrderedDict((
            ("overall", tally(lambda d: True)),
            ("PHONE", tally(lambda d: d["expected_binding_method"] == "PHONE")),
            ("NAME_AND_POSTAL_CODE", np_stat),
            ("EXPECTED_TO_FAIL",
             tally(lambda d: d["expected_binding_method"] == "EXPECTED_TO_FAIL")),
        ))),
        ("controls", OrderedDict((
            ("protected_rows", list(PROTECTED)),
            ("protected_bound_after", protected_binds_new),
            ("watched_rows", list(WATCHED)),
            ("watched_bound_after", watched_binds_new),
            ("all_held", not protected_binds_new and not watched_binds_new),
        ))),
        ("newly_accepted", [OrderedDict((
            ("identity_key", d["identity_key"]), ("url", d["url"]),
            ("rule", d["rule_that_changed_it"]),
            ("census", d["new_normalized_census"]),
            ("places", d["new_normalized_places"]))) for d in newly]),
        ("bindings_lost", [d["identity_key"] for d in lost]),
        ("still_rejected", [OrderedDict((
            ("identity_key", d["identity_key"]), ("why", d["why_unbound"]),
            ("census", d["new_normalized_census"]),
            ("places", d["new_normalized_places"])))
            for d in detail if d["new_decision"] == "UNBOUND"]),
        ("false_or_ambiguous_bindings", protected_binds_new + watched_binds_new),
        ("projection_for_the_remaining_118", OrderedDict((
            ("basis", "the NEW NAME_AND_POSTAL_CODE rate only. All 5 "
                      "phone-bearing rows in the 143 were taken into this "
                      "sample, so none remain and the 5/5 PHONE rate cannot "
                      "be applied."),
            ("new_name_and_postal_rate", round(new_rate, 4)),
            ("remaining", remaining),
            ("projected_urls", int(round(remaining * new_rate))),
            ("projected_requests", remaining),
        ))),
        ("qualification", OrderedDict((
            ("controls_held", not protected_binds_new),
            ("wrong_hotels_held", not watched_binds_new),
            ("no_binding_lost", not lost),
            ("name_and_postal_improved", improved),
            ("decision", "QUALIFY_REMAINING_118" if (safe and improved)
                         else "DO_NOT_QUALIFY"),
        ))),
        ("rows", detail),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = build()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    for group, stat in result["totals"].items():
        print("  %-22s old=%s new=%s of %s"
              % (group, stat["old"], stat["new"], stat["attempted"]))
    print("  controls held        %s" % result["controls"]["all_held"])
    print("  newly accepted       %d" % len(result["newly_accepted"]))
    print("  bindings lost        %d" % len(result["bindings_lost"]))
    projection = result["projection_for_the_remaining_118"]
    print("  projected for 118    %d urls from %d requests (rate %s)"
          % (projection["projected_urls"], projection["projected_requests"],
             projection["new_name_and_postal_rate"]))
    print("  DECISION             %s" % result["qualification"]["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
