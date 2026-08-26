"""PTF-GENERIC-PRE-ACQUISITION-DEDUP-HARDENING-001 -- decide duplicates BEFORE
the money, not after it.

The gap this closes
-------------------
``census_duplicate_scan`` reports beautifully and merges nothing, by design: a
person decides. But the factory only runs it in ``founder_review_packet``,
phase 13 -- five phases AFTER the cost plan and the paid pass. By the time it
speaks, the duplicates have already been routed twice, bought twice, and read
twice, and the founder is reviewing contradictory observations of one building
that Atlas paid for two of.

Grand Rapids-Holland made that concrete. Its re-census merged 113 fresh
discovery candidates with 103 recandidated prior identities; street absorption
caught 17, and the rest arrived as pairs -- a bare OpenStreetMap brand name and
a fully qualified prior-census name for one building::

    'ac hotel'            + 'ac hotel grand rapids downtown'   tel 6167763200
    'the bluejay hotel'   + 'the blue jay hotel and events'    644 bridge st nw

47 groups over 68 of 163 identities. Every one of those is a candidate for
paying twice.

What this module does, and what it refuses to do
------------------------------------------------
It is the SAME signals as the closure scan -- deliberately, because two
duplicate rules that can disagree are worse than one that is occasionally
conservative. What it adds is a verdict, and the verdict is conservative:

* MERGE only on a shared signal AND compatible names, where "compatible" is
  ``census_projection``'s existing token-containment rule and nothing looser.
  Never on name similarity, never on proximity, never on a shared brand.
* DISTINCT when the evidence affirmatively says two properties: property codes
  that differ, or incompatible names at one street or one switchboard. A
  dual-brand building is real (Louisville's Hampton Inn and Home2 Suites share
  1150 Forest Bridge Road) and must keep both rows and both purchases.
* DUPLICATE_REVIEW_REQUIRED when two identities claim ONE PAGE -- one canonical
  URL or one property code -- and their names do not agree. At most one of them
  can be right about that page, so both rows are kept, nothing is discarded,
  and only ONE is allowed to reach the paid cohort.

Why "same street, different names" is distinct but "same URL, different names"
is held
------------------------------------------------------------------------------
Because the question is not "are these the same building?" -- it is "would
buying both spend twice for one answer?". Two hotels at one address fetch two
different pages and produce two different policies: two purchases, two answers,
no waste. Two identities pointing at ONE URL fetch the SAME page twice: one
answer, two charges, and a second profile carrying another building's policy.
The spend test is the URL, which is why the cohort backstop in
``market_paid_acquisition`` keys on it and not on the identity key.
"""

from __future__ import annotations

import re
from collections import OrderedDict, defaultdict
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery.census_projection import (
    absorption_direction, names_equal_for_absorption,
)
from scripts.pettripfinder.discovery.census_url_recovery import digits, street_key

SCHEMA = "ptf-pre-acquisition-dedup/1.0"

#: Verdicts.
MERGE = "SAFE_MERGE"
DISTINCT = "DISTINCT_PROPERTIES"
REVIEW = "DUPLICATE_REVIEW_REQUIRED"

#: Signals that identify a PAGE. Two identities sharing one of these would be
#: bought twice for one answer.
PAGE_SIGNALS = ("CANONICAL_URL", "PROPERTY_CODE")
#: Signals that identify a BUILDING or a switchboard. Shared legitimately by
#: genuinely distinct hotels.
PREMISES_SIGNALS = ("STREET_AND_POSTAL_CODE", "TELEPHONE")

#: Brand property codes as they appear in canonical reservation URLs. Each is a
#: brand's own primary key for a building, so two rows carrying different codes
#: are two buildings on the brand's own authority -- which outranks every other
#: signal here, including a shared address.
#:
#: SCOPED TO THE BRAND'S OWN HOST, and the code must be followed by the slug
#: separator. A loose pattern here is not a missed merge, it is a WRONG one:
#: an earlier version matched ``/hotels/([a-z0-9]{5,10})[-/]`` against
#: ``marriott.com/hotels/travel/sdffy-fairfield-inn...``, read the literal path
#: segment "travel" as a property code, and collapsed four distinct Louisville
#: Marriotts into one page -- which would have suppressed three legitimate
#: purchases. Louisville's own compatibility test caught it. Requiring the
#: trailing ``-`` is what separates a code from a path keyword.
_PROPERTY_CODE_PATTERNS = (
    # hilton.com/en/hotels/GRRDTDT-canopy-grand-rapids/
    (re.compile(r"(?:^|\.)hilton\.com$", re.I),
     re.compile(r"/hotels/([a-z0-9]{5,9})-", re.I)),
    # marriott.com/hotels/travel/SDFLM-louisville-marriott-downtown
    # marriott.com/en-us/hotels/GRRAD-ac-hotel-grand-rapids/
    (re.compile(r"(?:^|\.)marriott\.com$", re.I),
     re.compile(r"/(?:travel|hotels)/([a-z0-9]{5,7})-", re.I)),
)


def canonical_url(row: Mapping) -> str:
    """The comparison form of a row's official URL: no trailing slash, no
    scheme or www difference, lower case. Anything that would fetch the same
    page must compare equal, or the double-buy guard has a hole in it."""
    url = (row.get("official_url") or "").strip().lower()
    if not url:
        return ""
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    url = url.split("#", 1)[0].rstrip("/")
    return url


def property_code(row: Mapping) -> str:
    """The brand's own key for this building, read off its canonical URL.

    Absent for an independent hotel, and absence is never evidence of anything:
    two rows with no code are simply not decided by this signal.
    """
    url = canonical_url(row)
    if not url:
        return ""
    host = url.split("/", 1)[0].split(":", 1)[0]
    path = url[len(host):]
    for host_pattern, code_pattern in _PROPERTY_CODE_PATTERNS:
        if not host_pattern.search(host):
            continue
        found = code_pattern.search(path)
        if found:
            return found.group(1).upper()
    return ""


def names_compatible(a_name: str, b_name: str) -> bool:
    """One name is a strict token subset of the other, or they are equal.

    ``census_projection``'s rule, reused rather than re-derived: an unqualified
    brand name is a subset of its qualified form ("ac hotel" of "ac hotel grand
    rapids downtown") and never the reverse, and both names must carry at least
    two tokens so a one-word row can never absorb half a market.

    "comfort inn" and "comfort suites grandville grand rapids sw" are NOT
    compatible under this rule and must not be merged by it -- Comfort Inn and
    Comfort Suites are two brands, and the shared switchboard that grouped them
    is a fact about a phone line, not about a building.
    """
    return (absorption_direction(a_name, b_name) != 0
            or names_equal_for_absorption(a_name, b_name))


def _signal_values(row: Mapping) -> Dict[str, str]:
    return {
        "CANONICAL_URL": canonical_url(row),
        "PROPERTY_CODE": property_code(row),
        "STREET_AND_POSTAL_CODE": street_key(row.get("address", ""),
                                             row.get("postal_code", "")),
        "TELEPHONE": digits(row.get("phone", "")),
    }


def _codes_disagree(rows: Sequence[Mapping]) -> bool:
    """Two rows carrying DIFFERENT brand property codes are two buildings.

    The brand is the authority on its own inventory, so this outranks a shared
    address: it is exactly the dual-brand tower the closure scan warns about.
    """
    codes = {property_code(r) for r in rows} - {""}
    return len(codes) > 1


def _rank(row: Mapping) -> Tuple:
    """Which row of a mergeable pair keeps the identity. Deterministic and total.

    The QUALIFIED name wins first, and that ordering is load-bearing rather
    than cosmetic. ``census_projection`` absorbs a strict token-subset into its
    superset and never the reverse, because a bare brand name is the worse
    identity: "ac hotel" names no building, "ac hotel grand rapids downtown"
    names one. Ranking by populated fields first inverted that on real data --
    whichever sighting happened to carry more columns won, and 9 of 21 Grand
    Rapids merges kept the bare OpenStreetMap name over the qualified
    prior-census one. Evidence still breaks ties between names of equal
    qualification, which is the case ``names_equal_for_absorption`` covers.
    """
    return (
        len((row.get("canonical_name") or "").split()),
        1 if (row.get("official_url") or "").strip() else 0,
        1 if (row.get("address") or "").strip() else 0,
        1 if (row.get("postal_code") or "").strip() else 0,
        1 if (row.get("phone") or "").strip() else 0,
        row.get("identity_key") or "",
    )


def _verdict(signal: str, rows: Sequence[Mapping]) -> Tuple[str, str]:
    """``(verdict, why)`` for one group sharing one signal value."""
    if _codes_disagree(rows):
        return (DISTINCT,
                "the rows carry different brand property codes (%s); the brand "
                "is the authority on its own inventory, so this is a shared "
                "building holding distinct properties"
                % ", ".join(sorted({property_code(r) for r in rows} - {""})))

    names = [r.get("canonical_name") or "" for r in rows]
    all_compatible = all(
        names_compatible(names[i], names[j])
        for i in range(len(names)) for j in range(i + 1, len(names)))

    if all_compatible:
        return (MERGE,
                "one %s and names that agree by token containment: a bare name "
                "and its qualified form for one property" % signal.lower())
    if signal in PAGE_SIGNALS:
        # At most one of these rows can legitimately own the page. Both are
        # kept; only one may be bought.
        return (REVIEW,
                "two identities claim one %s but their names do not agree; at "
                "most one of them owns that page, and buying both would pay "
                "twice for one answer" % signal.lower())
    return (DISTINCT,
            "the rows share a %s but their names are not containment-"
            "compatible; distinct hotels legitimately share a street address "
            "and a switchboard, and they fetch different pages"
            % signal.lower())


def analyse(rows: Sequence[Mapping]) -> Dict:
    """The pre-acquisition dedup decision over a proposed census.

    Returns groups with verdicts, the merge plan, and the set of identity keys
    that must NOT reach the paid cohort. Pure: reads rows, writes nothing,
    fetches nothing, spends nothing.
    """
    by_key = {r["identity_key"]: r for r in rows}
    groups: List[Dict] = []

    for signal in PAGE_SIGNALS + PREMISES_SIGNALS:
        buckets: Dict[str, List[str]] = defaultdict(list)
        for row in rows:
            value = _signal_values(row)[signal]
            if value:
                buckets[value].append(row["identity_key"])
        for value, keys in sorted(buckets.items()):
            if len(keys) < 2:
                continue
            members = [by_key[k] for k in sorted(keys)]
            verdict, why = _verdict(signal, members)
            groups.append(OrderedDict((
                ("signal", signal),
                ("value", value),
                ("identity_keys", sorted(keys)),
                ("size", len(keys)),
                ("verdict", verdict),
                ("why", why),
            )))

    # A merge is applied only when NO other group holds the same rows apart.
    # A pair that one signal would merge and another calls DISTINCT is not a
    # merge: the affirmative evidence wins, because unmerging a census after
    # publication is far more expensive than reviewing one row.
    distinct_pairs = set()
    for group in groups:
        if group["verdict"] == DISTINCT:
            keys = group["identity_keys"]
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    distinct_pairs.add((keys[i], keys[j]))

    merges: List[Dict] = []
    absorbed_into: Dict[str, str] = {}
    for group in groups:
        if group["verdict"] != MERGE:
            continue
        keys = group["identity_keys"]
        blocked = [(keys[i], keys[j])
                   for i in range(len(keys)) for j in range(i + 1, len(keys))
                   if (keys[i], keys[j]) in distinct_pairs]
        if blocked:
            group["verdict"] = REVIEW
            group["why"] = ("a stronger signal holds these rows apart as "
                            "distinct properties, so the merge is withheld and "
                            "the group is left for review")
            continue
        members = sorted((by_key[k] for k in keys), key=_rank, reverse=True)
        keeper = members[0]["identity_key"]
        for row in members[1:]:
            key = row["identity_key"]
            if key in absorbed_into or keeper in absorbed_into:
                continue
            absorbed_into[key] = keeper
            merges.append(OrderedDict((
                ("absorbed", key),
                ("into", keeper),
                ("signal", group["signal"]),
                ("value", group["value"]),
                ("why", group["why"]),
            )))

    # Rows held for review: every member but the best-ranked one is barred from
    # the paid cohort. Nothing is discarded -- the census keeps both rows.
    withheld: Dict[str, str] = {}
    for group in groups:
        if group["verdict"] != REVIEW:
            continue
        members = sorted((by_key[k] for k in group["identity_keys"]),
                         key=_rank, reverse=True)
        allowed = members[0]["identity_key"]
        for row in members[1:]:
            key = row["identity_key"]
            if key in absorbed_into:
                continue
            withheld.setdefault(key, (
                "held by %s %r: %s may buy this page for the group"
                % (group["signal"].lower(), group["value"], allowed)))

    counts = OrderedDict()
    for verdict in (MERGE, REVIEW, DISTINCT):
        counts[verdict] = sum(1 for g in groups if g["verdict"] == verdict)

    return OrderedDict((
        ("schema", SCHEMA),
        ("identities_in", len(rows)),
        ("groups_found", len(groups)),
        ("groups_by_verdict", counts),
        ("merged_identities", len(absorbed_into)),
        ("withheld_from_acquisition", len(withheld)),
        ("identities_out", len(rows) - len(absorbed_into)),
        ("merges", merges),
        ("withheld", OrderedDict(sorted(withheld.items()))),
        ("groups", groups),
    ))


def payable_keys(rows: Sequence[Mapping], analysis: Optional[Mapping] = None
                 ) -> List[str]:
    """The identity keys that may reach the paid cohort, in census order."""
    analysis = analysis if analysis is not None else analyse(rows)
    barred = set(analysis["withheld"]) | {m["absorbed"] for m in analysis["merges"]}
    return [r["identity_key"] for r in rows if r["identity_key"] not in barred]
