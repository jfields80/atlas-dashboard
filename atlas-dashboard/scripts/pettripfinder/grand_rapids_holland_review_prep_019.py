# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-REVIEW-PROMOTION-PREP-019 -- prepare the market on
evidence we already own.

NO PROVIDER IS CALLED. No Places lookup, no Bright Data session, no Firecrawl
credit, no discovery. Every fact below is read off an artifact already committed
to this branch or a capture already saved on disk, and the run spends nothing.

WHAT THIS BUILDS, AND WHAT IT REFUSES TO BUILD
-----------------------------------------------
Four documents: an exception-only review packet, a routing-repair adjudication,
the identity-hold dossier, and a proposed-authority CANDIDATE list.

The fourth is a candidate list and not an authority. ``market_proposed_authority_cli``
gates on the founder's decision ledger -- "only a row the founder SIGNED" -- and
this market's founder review has not run: ``founder_review`` is NOT_RUN in the
factory ledger. So no decision, reviewer id or timestamp is written anywhere by
this module, and the candidate list says what WOULD become authority once
signed, with the semantic-approval hash that binds each signature to the exact
evidence it approves.

WHY AN EXCEPTION-ONLY PACKET IS SAFE
-------------------------------------
45 of the 54 rows carry a VALID membrane verdict, a publication-grade capture,
and a machine review that found nothing to correct. Asking a person to read
those one at a time is how a real exception gets lost in a stack of clean ones.
They are still SIGNED -- a machine review is not an approval and this module
writes none -- but they are signed as a class, and the nine exceptions are the
only rows that need a reading. Every clean row still carries its own semantic
hash, so a class signature still binds to specific evidence rather than to a
count.

THE EIGHT "ROUTING REPAIRS" ARE MOSTLY NOT ROUTING DEFECTS
------------------------------------------------------------
That is this pass's main finding. The cross-run ledger calls a prior
IDENTITY_MISMATCH ``SUPPRESSED_ROUTING_REPAIR_REQUIRED`` because the general
case is a row pointed at the wrong page. Here, seven of the eight URLs already
resolve to the property's own page and the page's title names the property; what
failed is the identity gate's CORROBORATION -- the page prints no telephone, or
the census address is corrupt, or the name was rebranded. One URL is a genuine
404. One route names a different brand than the row does. None of those is fixed
by a purchase, and only the last is fixed by re-routing.

Every one of the eight has its declined capture still on disk, so a founder
ruling on identity costs nothing to act on afterwards. That is worth saying
plainly: the evidence is bought and kept, and what is missing is a decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata.corpus import BRAND_HOSTS, brand_of  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RUN_DIR = (_REPO_ROOT / "data" / "acquisition"
           / "grand_rapids_holland_mi_factory_001" / "pass1")

WORK_ORDER = "PTF-GRAND-RAPIDS-FOUNDER-REVIEW-PROMOTION-PREP-019"
MARKET = "grand-rapids-holland-mi"
BINDING_CONTRACT = "semantic-approval/1.0"

#: Nothing in this module may write one of these. The founder review for this
#: market has not run; a machine's opinion stays a machine's opinion.
PENDING = "MACHINE_REVIEWED_PENDING_OPERATOR"


# --------------------------------------------------------------------------- #
# Phase 1 -- the classes, and the ladder that assigns them
# --------------------------------------------------------------------------- #

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"
POLICY_FACT_CORRECTION = "POLICY_FACT_CORRECTION"
IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
HOLD_ALLOWANCE_NOT_STATED = "HOLD_ALLOWANCE_NOT_STATED"
HOLD_SOURCE_SILENT_ON_PETS = "HOLD_SOURCE_SILENT_ON_PETS"

CLEAN_CLASSES: Tuple[str, ...] = (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS)
EXCEPTION_CLASSES: Tuple[str, ...] = (POLICY_FACT_CORRECTION, IDENTITY_CONFLICT,
                                      HOLD_ALLOWANCE_NOT_STATED,
                                      HOLD_SOURCE_SILENT_ON_PETS)
ALL_CLASSES: Tuple[str, ...] = CLEAN_CLASSES + EXCEPTION_CLASSES


def classify_reusable(key: str, store: Mapping, packet: Mapping,
                      analysis: Mapping) -> Tuple[str, str]:
    """``(class, why)`` for one REUSABLE_POLICY_EVIDENCE row.

    Rungs are tried top-down and the first that fires wins, the same order
    ``founder_review_analysis`` uses and for the same reason: a row can trip
    several and the most cautious answer has to survive.
    """
    record = store.get(key)
    if record is None:
        # POLICY_NOT_FOUND. The page served and said nothing about pets, which
        # is a durable finding about the SOURCE and not a statement that the
        # hotel refuses animals. It produces no publication-grade record, so it
        # never reached the review packet at all.
        return (HOLD_SOURCE_SILENT_ON_PETS,
                "the page rendered and never mentions pets; a silent source is "
                "not a no-pets policy, and this market has no founder rule on "
                "silence yet")

    verdict = str((record.get("membrane") or {}).get("verdict") or "")
    if verdict != "VALID":
        return (IDENTITY_CONFLICT,
                "the membrane refuses this observation as being about another "
                "property (%s); no correction to the facts changes that, and a "
                "person decides whether the page and the census name one "
                "building" % (verdict or "no verdict"))

    proposed = str((analysis.get(key) or {}).get("proposed_disposition") or "")
    if proposed == "HOLD":
        return (HOLD_ALLOWANCE_NOT_STATED,
                "the source prices or limits a pet without ever stating that "
                "pets are accepted, so pets_allowed is withheld as "
                "SOURCE_SILENT; reading an allowance out of a price is an "
                "inference this codebase will not make")
    if proposed == "APPROVE_WITH_CHANGE":
        return (POLICY_FACT_CORRECTION,
                "the facts stand but the record as written would mislead a "
                "guest; the correction only removes something unsupported or "
                "replaces a value with one the evidence already states")
    if proposed == "APPROVE_VERIFIED_NO_PETS":
        return (CLEAN_VERIFIED_NO_PETS,
                "the property's own page states that pets are not accepted; "
                "membrane VALID, publication-grade, nothing to correct")
    if proposed == "APPROVE_PET_FRIENDLY":
        return (CLEAN_PET_FRIENDLY,
                "the property's own page states that pets are accepted; "
                "membrane VALID, publication-grade, nothing to correct")
    raise ValueError("no disposition for %r; a row with no proposed "
                     "disposition must not be filed as clean" % key)


# --------------------------------------------------------------------------- #
# Phase 2 -- what is actually wrong with each unresolved row
# --------------------------------------------------------------------------- #

ROUTE_IS_DEAD = "ROUTE_IS_DEAD"
ROUTE_NAMES_ANOTHER_BRAND = "ROUTE_NAMES_ANOTHER_BRAND"
ROUTE_REDIRECTED_OFF_THE_PROPERTY = "ROUTE_REDIRECTED_OFF_THE_PROPERTY"
ROUTE_REFUSED_BY_THE_SITE = "ROUTE_REFUSED_BY_THE_SITE"
ROUTE_IS_CORRECT_IDENTITY_UNCORROBORATED = "ROUTE_IS_CORRECT_IDENTITY_UNCORROBORATED"

#: Brand words that appear in a hotel's NAME, mapped to the brand label
#: ``corpus.BRAND_HOSTS`` already uses for that chain's own domain. The table is
#: deliberately tiny and is used only to REFUTE a route -- never to choose one.
#: A name that says "Best Western" and a URL that says wyndhamhotels.com
#: contradict each other on the two chains' own authority; that is a fact about
#: the route, and it is the only thing this table is allowed to conclude.
NAME_BRAND_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("best western", "BEST_WESTERN"), ("motel 6", "MOTEL6"),
    ("studio 6", "MOTEL6"), ("drury", "DRURY"), ("hyatt", "HYATT"),
    ("marriott", "MARRIOTT"), ("hilton", "HILTON"), ("red roof", "RED_ROOF"),
    ("extended stay america", "ESA"), ("sonesta", "SONESTA"),
    ("wyndham", "WYNDHAM"),
)

_BRAND_LABELS = frozenset(brand for _host, brand in BRAND_HOSTS)


def brand_contradiction(name: str, url: str) -> Tuple[str, str]:
    """``(name_brand, url_brand)`` when the two disagree, else ``("", "")``."""
    url_brand = brand_of(url)
    if url_brand not in _BRAND_LABELS:
        return ("", "")
    lowered = (name or "").lower()
    for marker, name_brand in NAME_BRAND_MARKERS:
        if marker in lowered and name_brand != url_brand:
            return (name_brand, url_brand)
    return ("", "")


def _capture_dir(slug_candidates: Sequence[str]) -> str:
    for slug in slug_candidates:
        for sub in ("declined-01", "attempt-01"):
            path = RUN_DIR / slug / sub
            if path.is_dir():
                return str(path.relative_to(_REPO_ROOT).as_posix())
    return ""


def _slugs(key: str, result: Mapping) -> List[str]:
    """Every directory name this row's capture might sit under.

    The runner slugs a row from its canonical name and drops the ampersand
    words, so ``baymont inn and suites ...`` lands in ``baymont-inn-suites-...``
    while ``the ada hotel`` keeps its shape. Both spellings are tried rather
    than guessing which rule was in force, and a directory that does not exist
    simply is not reported.
    """
    base = key.replace("&", "and")
    dashed = "-".join(base.split())
    return [dashed, "-".join(w for w in base.split() if w != "and")]


def owned_alternative(key: str, current: str, prior: Mapping) -> Dict:
    """Any official URL a PRIOR BUILD saved for this row, and whether it helps.

    This is the whole of what "repair it offline" can draw on: the earlier
    Grand Rapids build's final partition, which recorded an official URL per
    identity. Where it names a different URL the difference is reported -- and
    so is whether swapping it would change anything, because
    ``market_routing.apply_url_overlay`` refuses to displace a URL a lane can
    already fetch, and it is right to. A route that reaches the property's own
    page is not repaired by rewriting it into a prettier form of itself.
    """
    saved = str((prior.get(key) or {}).get("official_url") or "")
    if not saved or saved.rstrip("/") == (current or "").rstrip("/"):
        return OrderedDict((("exists", False), ("url", ""),
                            ("would_change_the_route", False),
                            ("why", "no prior build saved a different URL for "
                                    "this identity")))
    from scripts.pettripfinder.acquisition import market_routing as MR
    current_routable = MR.classify_url_shape(
        MR.normalize_source_url(current)) in MR.ROUTABLE_SHAPES
    return OrderedDict((
        ("exists", True), ("url", saved),
        ("would_change_the_route", not current_routable),
        ("why", "the route this row already carries is a %s that a lane can "
                "fetch, and the overlay contract refuses to displace one; the "
                "saved URL is the stable canonical form of the SAME page, not "
                "a different page" % MR.classify_url_shape(
                    MR.normalize_source_url(current))
         if current_routable else
         "the current route is unfetchable and the saved URL is routable, so "
         "layering it as an overlay is a real repair"),
    ))


#: What the identity gate said was missing, keyed on the phrase it uses to say
#: it. Reading the gate's own words is better than re-deriving the comparison
#: from the census, because the gate compared what it actually saw on the page
#: and this module has only the census side of that.
MISSING_SIGNALS: Tuple[Tuple[str, str], ...] = (
    ("declares no telephone", "the page prints no telephone of its own"),
    ("page street", "the page's street does not match the census address"),
    ("page names", "the page's name does not match the census name, which "
                   "usually means a rebrand"),
    ("names agree only on", "the names share only words this market's hotels "
                            "all share, so the name proves nothing"),
)

#: A compound direction the census half-expanded: "SW" became "SouthW.". OSM
#: writes both forms and only this one breaks the street comparison.
_HALF_EXPANDED = re.compile(r"\b(North|South|East|West)(East|West|E|W)\.", re.I)


def uncorroborated_action(key: str, name: str, result: Mapping,
                          census: Mapping, twins: Mapping) -> str:
    """The exact thing that would settle THIS row, not a generic instruction."""
    detail = str(result.get("detail") or "").lower()
    missing = [text for phrase, text in MISSING_SIGNALS if phrase in detail]
    parts = ["founder identity ruling: %s" % ("; ".join(missing) or
                                              "no physical signal agreed")]
    address = str(census.get("address") or "")
    if _HALF_EXPANDED.search(address):
        parts.append("the census address %r half-expands a compound direction "
                     "and cannot match any page; correcting that one field is "
                     "an operator edit, not a ruling" % address)
    if not str(census.get("phone") or ""):
        parts.append("the census row states no telephone either, so the "
                     "strongest available signal is absent on BOTH sides")
    twin = twins.get(key)
    if twin:
        parts.append("a second census row %r shares this street, so the ruling "
                     "must also say whether they are one building" % twin)
    parts.append("the declined capture is saved, so acting on the ruling costs "
                 "nothing")
    return ". ".join(parts)


def street_twins(census: Mapping[str, Mapping]) -> Dict[str, str]:
    """Identity keys that share a normalised street and postal code."""
    groups: Dict[str, List[str]] = {}
    for key, row in census.items():
        address = " ".join(str(row.get("address") or "").lower().split())
        number = address.split(" ")[0] if address else ""
        postal = str(row.get("postal_code") or "")
        if number and postal:
            groups.setdefault("%s|%s" % (number, postal), []).append(key)
    out: Dict[str, str] = {}
    for members in groups.values():
        if len(members) == 2:
            out[members[0]], out[members[1]] = members[1], members[0]
    return out


def adjudicate_route(row: Mapping, result: Mapping, census: Mapping,
                     prior: Mapping, twins: Mapping) -> Dict:
    """One verdict and one next action for an unresolved row. Offline."""
    key = str(row.get("identity_key") or "")
    name = str(census.get("canonical_name") or row.get("canonical_name") or "")
    source = str(row.get("source_url") or "")
    final = str(result.get("final_url") or "")
    title = str(result.get("title") or "")
    outcome = str(result.get("outcome") or "")

    name_brand, url_brand = brand_contradiction(name, source)
    if name_brand:
        verdict = ROUTE_NAMES_ANOTHER_BRAND
        why = ("the census row is named %r and its official_url is a %s page; "
               "the two chains contradict each other on their own authority, "
               "so this route cannot be right whatever the page says"
               % (name, url_brand))
        action = ("REVOKE the route: clear official_url for %r and return it to "
                  "ROUTE_NEEDS_OFFICIAL_URL, then decide whether the OSM name "
                  "or the OSM url is the stale half. This is an operator edit "
                  "to the census, so it is proposed here and not applied."
                  % key)
    elif "page not found" in title.lower() or "404" in title:
        verdict = ROUTE_IS_DEAD
        why = ("the URL resolves, and the page it resolves to is the site's own "
               "not-found page (%r); there is no property page behind this "
               "route to corroborate or to read" % title)
        action = ("paid URL discovery for %r in a future work order; no artifact "
                  "on this branch names another URL for it" % key)
    elif outcome == "UNEXPECTED_PAGE":
        # The page-health gate has already ruled on this one; taking its verdict
        # is better than re-deriving it from a string comparison of the two
        # URLs, which gets a same-prefix redirect right and a cross-path one
        # wrong -- radissonhotels.com/.../hotels/country-inn-holland-mi lands on
        # /brand/country-inn, which shares no prefix and is still a brand page.
        verdict = ROUTE_REDIRECTED_OFF_THE_PROPERTY
        why = ("the property URL redirected to %r (%r), which is a brand page "
               "and nobody's official URL; the page-health gate rejected it"
               % (final, title))
        action = ("paid URL discovery for %r, or a first-party URL recovered "
                  "from a source family this branch has not searched" % key)
    elif outcome == "NAVIGATION_FAILED":
        verdict = ROUTE_REFUSED_BY_THE_SITE
        why = ("the site refused the fetch (%s) so no page was ever seen; the "
               "route is unproven rather than wrong"
               % (str(result.get("detail") or "").split("Error:")[-1].strip()[:120]))
        action = ("re-attempt on a permitted lane the ledger has not spent for "
                  "this page, in a work order that authorises the spend")
    else:
        verdict = ROUTE_IS_CORRECT_IDENTITY_UNCORROBORATED
        why = ("the URL resolves to a property page whose title (%r) names this "
               "property; the identity gate refused on corroboration, not on "
               "the route -- %s" % (title, str(result.get("detail") or "")[:150]))
        action = uncorroborated_action(key, name, result, census, twins)

    return OrderedDict((
        ("identity_key", key),
        ("canonical_name", name),
        ("prior_outcome", outcome),
        ("source_url", source),
        ("final_url", final),
        ("page_title", title),
        ("verdict", verdict),
        ("owned_alternative_url", owned_alternative(key, source, prior)),
        ("repairable_offline", False),
        ("repaired_offline", False),
        ("why", why),
        ("next_action", action),
        ("saved_capture", _capture_dir(_slugs(key, result))),
        ("census_address", str(census.get("address") or "")),
        ("census_phone", str(census.get("phone") or "")),
        ("gate_detail", str(result.get("detail") or "")),
    ))


# --------------------------------------------------------------------------- #
# Phase 3 -- the identity holds
# --------------------------------------------------------------------------- #

#: The two the work order names. Each is a pair of census rows that share a
#: street and a switchboard and nothing else, which is precisely the evidence
#: PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018 stopped the paid ledger from
#: deciding on. They are carried here so a founder can rule, not so this module
#: can.
NAMED_HOLDS: Tuple[Tuple[str, str], ...] = (
    ("comfort inn", "comfort suites grandville grand rapids sw"),
    ("sleep inn and suites", "spark by hilton grand rapids"),
)

#: What would settle each hold, stated as evidence rather than as an opinion.
EVIDENCE_NEEDED: Tuple[str, ...] = (
    "either property's own page naming its street address, so the two pages can "
    "be compared instead of the two census rows",
    "a brand property code for each half; Choice publishes one that this "
    "project's URL patterns do not currently extract, and a code on each side "
    "settles the question outright",
    "a state lodging-registry entry, or a county parcel record, showing one "
    "licence or two at the shared address",
)


def _same_phone_finding(same_phone: Sequence[Mapping]) -> str:
    unnamed = [s for s in same_phone if not s["is_a_named_hold"]]
    if not unnamed:
        return ("%d pairs share an identical switchboard AND were ruled "
                "distinct, and this work order names all of them"
                % len(same_phone))
    return ("%d pairs share an identical switchboard AND were ruled distinct. "
            "Two are the holds this work order names; %s the same shape and "
            "%s had no separate reading: %s"
            % (len(same_phone),
               "the one that remains is" if len(unnamed) == 1
               else "the %d that remain are" % len(unnamed),
               "has" if len(unnamed) == 1 else "have",
               "; ".join(" / ".join(s["identity_keys"]) for s in unnamed)))


def build_holds(census: Mapping[str, Mapping], dedup: Mapping,
                routing: Mapping[str, Mapping],
                payable_keys: Sequence[str]) -> Dict:
    groups: Dict[Tuple[str, str], str] = {}
    for group in dedup.get("groups") or ():
        keys = tuple(sorted(str(k) for k in group.get("identity_keys") or ()))
        if len(keys) == 2:
            groups.setdefault(keys, str(group.get("verdict") or ""))

    rows = []
    for left, right in NAMED_HOLDS:
        halves = []
        for key in (left, right):
            row = census.get(key) or {}
            halves.append(OrderedDict((
                ("identity_key", key),
                ("canonical_name", str(row.get("canonical_name") or "")),
                ("address", str(row.get("address") or "")),
                ("postal_code", str(row.get("postal_code") or "")),
                ("phone", str(row.get("phone") or "")),
                ("official_url", str(row.get("official_url") or "")),
                ("routing_state", str((routing.get(key) or {})
                                      .get("routing_state") or "NOT_ROUTED")),
                ("in_authority_candidates", key in set(payable_keys)),
            )))
        rows.append(OrderedDict((
            ("identity_keys", [left, right]),
            ("dedup_verdict", groups.get(tuple(sorted((left, right))),
                                         "NOT_GROUPED")),
            ("shared_signals", ["STREET_AND_POSTAL_CODE", "TELEPHONE"]),
            ("resolved_by_this_pass", False),
            ("merged_by_this_pass", False),
            ("decided_on_shared_telephone", False),
            ("halves", halves),
            ("evidence_that_would_settle_it", list(EVIDENCE_NEEDED)),
            ("why_it_is_still_open",
             "a shared street and a shared switchboard describe a BUILDING. "
             "Two hotels in one building share both, and so does a hotel and "
             "the brand it was renamed from. Neither this module nor the paid "
             "ledger may decide which; a person does."),
        )))
    # Every pair the dedup gate ruled DISTINCT_PROPERTIES on a shared street is
    # the same KIND of question the two named holds are; the gate simply
    # answered it. Surfacing the whole class, and flagging which pairs also
    # share an identical switchboard, is what lets a founder see that the two
    # they were asked about are not the only two -- without this module
    # promoting any of them into a hold on its own authority.
    named = {frozenset(pair) for pair in NAMED_HOLDS}
    surfaced = []
    for group in dedup.get("groups") or ():
        keys = sorted(str(k) for k in group.get("identity_keys") or ())
        if len(keys) != 2 or group.get("verdict") != "DISTINCT_PROPERTIES":
            continue
        if frozenset(keys) in {frozenset(s["identity_keys"])
                               for s in surfaced}:
            continue
        left, right = keys
        phones = [str((census.get(k) or {}).get("phone") or "") for k in keys]
        surfaced.append(OrderedDict((
            ("identity_keys", keys),
            ("is_a_named_hold", frozenset(keys) in named),
            ("shares_an_identical_telephone",
             bool(phones[0]) and phones[0] == phones[1]),
            ("telephones", phones),
            ("addresses", [str((census.get(k) or {}).get("address") or "")
                           for k in keys]),
            ("routing_states", [str((routing.get(k) or {})
                                    .get("routing_state") or "NOT_ROUTED")
                                for k in keys]),
            ("in_authority_candidates",
             sorted(set(keys) & set(payable_keys))),
        )))
    surfaced.sort(key=lambda s: (not s["shares_an_identical_telephone"],
                                 s["identity_keys"]))
    same_phone = [s for s in surfaced if s["shares_an_identical_telephone"]]

    return OrderedDict((
        ("count", len(rows)),
        ("holds", rows),
        ("surfaced_identity_questions", OrderedDict((
            ("what_this_is",
             "every pair the pre-acquisition dedup gate ruled "
             "DISTINCT_PROPERTIES on a shared street. The gate ANSWERED these; "
             "they are listed so a founder can see the class the two named "
             "holds belong to, and nothing here is promoted to a hold."),
            ("pairs_ruled_distinct", len(surfaced)),
            ("of_those_sharing_an_identical_telephone", len(same_phone)),
            ("named_by_the_work_order", sum(1 for s in surfaced
                                            if s["is_a_named_hold"])),
            ("finding", _same_phone_finding(same_phone)),
            ("pairs", surfaced),
        ))),
    ))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shard_baseline() -> Dict:
    """What this market's REGISTERED authority holds today.

    Grand Rapids is already a registered market -- it has a contract in
    ``markets/`` and a shard in ``markets/authority/`` -- but a discovery-stage
    one: its own contract says "No pet-policy claim is published from it", it is
    hidden from navigation and sitemap, and it carries zero exclusions and zero
    affiliate destinations. So a promotion here is not a registration, and the
    deployment-record coupling PTF-047 established does not fire. It is the
    first policy content this market would publish, which is why the baseline
    belongs in the artifact rather than in somebody's memory.
    """
    shard = (LP / "markets" / "authority" / MARKET)
    contract_path = LP / "markets" / ("%s.json" % MARKET)
    out = OrderedDict((("shard_dir", str(shard.relative_to(_REPO_ROOT).as_posix())),
                       ("exists", shard.is_dir())))
    for name, field in (("hotel_exclusions.json", "exclusions"),
                        ("identity_routing.json", "routes"),
                        ("affiliate_destinations.json", "destinations")):
        path = shard / name
        out[field] = (len(json.loads(path.read_text(encoding="utf-8"))
                          .get(field) or ()) if path.is_file() else None)
        out["%s_sha256" % field] = _sha256(path) if path.is_file() else ""
    if contract_path.is_file():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        out["show_in_navigation"] = bool(contract.get("show_in_navigation"))
        out["show_in_sitemap"] = bool(contract.get("show_in_sitemap"))
        out["minimum_published_hotels"] = contract.get("minimum_published_hotels")
        out["introductory_copy"] = str(contract.get("introductory_copy") or "")
    out["unchanged_by_this_pass"] = True
    out["why"] = ("the market is registered but discovery-stage and publishes "
                  "no policy claim; promotion would be its first, and this pass "
                  "writes nothing into the shard")
    return out


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _header(schema: str, what: str, inputs: Mapping[str, Path]) -> "OrderedDict":
    return OrderedDict((
        ("schema", schema),
        ("what_this_is", what),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("inputs", OrderedDict(
            (name, OrderedDict((
                ("path", str(path.relative_to(_REPO_ROOT).as_posix())),
                ("sha256", _sha256(path)))))
            for name, path in inputs.items())),
    ))


def build(paths: Mapping[str, Path]) -> Dict[str, Dict]:
    replay = _load(paths["replay"])
    store_doc = _load(paths["store"])
    packet_doc = _load(paths["packet"])
    analysis_doc = _load(paths["analysis"])
    closeout = _load(paths["closeout"])
    census_doc = _load(paths["census"])
    dedup = _load(paths["dedup"])
    routing_doc = _load(paths["routing"])

    store = {r["identity_key"]: r for r in store_doc["records"]}
    packet = {c["identity_key"]: c for c in packet_doc["candidates"]}
    analysis = {r["identity_key"]: r for r in analysis_doc["rows"]}
    results = {r["identity_key"]: r for r in closeout["results"]}
    census = {h["identity_key"]: h for h in census_doc["hotels"]}
    routing = {e["identity_key"]: e for e in routing_doc["entries"]}

    by_class = {row["identity_key"]: row["classification"]
                for row in replay["rows"]}
    reusable = [k for k, v in by_class.items()
                if v == "REUSABLE_POLICY_EVIDENCE"]
    repair = [k for k, v in by_class.items() if v == "ROUTING_REPAIR_REQUIRED"]
    failed = [k for k, v in by_class.items() if v == "SAME_PAGE_ALREADY_FAILED"]

    # ------------------------------------------------------------------ #
    # Phase 1
    # ------------------------------------------------------------------ #
    rows: List[Dict] = []
    for key in sorted(reusable):
        klass, why = classify_reusable(key, store, packet, analysis)
        candidate = packet.get(key) or {}
        record = store.get(key) or {}
        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", str(candidate.get("canonical_name")
                                   or record.get("canonical_name")
                                   or (census.get(key) or {}).get("canonical_name")
                                   or "")),
            ("classification", klass),
            ("needs_individual_founder_reading", klass in EXCEPTION_CLASSES),
            ("why", why),
            ("membrane_verdict", str((record.get("membrane") or {})
                                     .get("verdict") or "NO_RECORD")),
            ("readiness", str(record.get("readiness") or "NO_RECORD")),
            ("publication_grade", bool(record.get("publication_grade"))),
            ("machine_recommendation", str(candidate.get("recommendation") or "")),
            ("proposed_disposition",
             str((analysis.get(key) or {}).get("proposed_disposition") or "")),
            ("source_url", str(candidate.get("source_url")
                               or (results.get(key) or {}).get("source_url") or "")),
            ("snapshot_hash", str(candidate.get("snapshot_hash") or "")),
            ("semantic_approval_hash",
             str((candidate.get("semantic_approval") or {}).get("semantic_hash") or "")),
            # Never filled in here. See the module docstring.
            ("review_status", PENDING),
            ("founder_decision", ""),
            ("founder_reviewer_id", ""),
            ("founder_reviewed_at", ""),
        ))
        if klass in EXCEPTION_CLASSES:
            entry = analysis.get(key) or {}
            row["required_changes"] = entry.get("required_changes") or []
            row["findings"] = entry.get("findings") or []
            row["next_action"] = str(entry.get("next_action") or "")
            row["reasons"] = entry.get("reasons") or []
        rows.append(row)

    counts = Counter(r["classification"] for r in rows)
    exceptions = [r for r in rows if r["needs_individual_founder_reading"]]
    clean = [r for r in rows if not r["needs_individual_founder_reading"]]

    packet_019 = _header(
        "ptf-exception-review-packet/1.0",
        "The 54 rows whose policy evidence this project already owns, split "
        "into the nine a founder must read and the 45 that a class signature "
        "can cover. Nothing here is an approval.",
        {k: paths[k] for k in ("replay", "store", "packet", "analysis")})
    packet_019.update(OrderedDict((
        ("binding_contract", BINDING_CONTRACT),
        ("approval_vocabulary", packet_doc.get("approval_vocabulary", "")),
        ("founder_instructions", packet_doc.get("founder_instructions", "")),
        ("reusable_rows", len(rows)),
        ("by_classification", OrderedDict(
            (name, counts.get(name, 0)) for name in ALL_CLASSES)),
        ("exceptions_requiring_a_reading", len(exceptions)),
        ("clean_rows_coverable_by_a_class_signature", len(clean)),
        ("why_a_class_signature_is_still_a_signature",
         "each clean row carries its own semantic-approval hash, so a signature "
         "over the class still binds to the exact facts of each record and "
         "still lapses if any of them moves. What the class saves is the "
         "reading, not the binding."),
        ("exceptions", exceptions),
        ("clean", clean),
    )))

    # ------------------------------------------------------------------ #
    # Phase 2
    # ------------------------------------------------------------------ #
    prior = {i["identity_key"]: i
             for i in _load(paths["prior_partition"])["items"]}
    twins = street_twins(census)
    adjudications = [adjudicate_route(routing.get(k, {"identity_key": k}),
                                      results.get(k, {}), census.get(k, {}),
                                      prior, twins)
                     for k in sorted(repair) + sorted(failed)]
    for entry in adjudications:
        entry["repairable_offline"] = bool(
            entry["owned_alternative_url"]["would_change_the_route"])
    verdicts = Counter(a["verdict"] for a in adjudications)
    brand_scan = [OrderedDict((("identity_key", e["identity_key"]),
                               ("canonical_name", e.get("canonical_name", "")),
                               ("name_brand", nb), ("url_brand", ub),
                               ("source_url", e.get("source_url", ""))))
                  for e in routing_doc["entries"]
                  if e.get("routing_state") == "ROUTED"
                  for nb, ub in [brand_contradiction(
                      str((census.get(e["identity_key"]) or {}).get("canonical_name")
                          or e.get("canonical_name") or ""),
                      str(e.get("source_url") or ""))]
                  if nb]

    repair_019 = _header(
        "ptf-routing-repair-adjudication/1.0",
        "Every unresolved routed row, adjudicated from artifacts and saved "
        "captures alone. No provider was called and no route was rewritten.",
        {k: paths[k] for k in ("replay", "closeout", "routing", "census",
                               "prior_partition")})
    repair_019.update(OrderedDict((
        ("rows_adjudicated", len(adjudications)),
        ("routing_repair_required_in", len(repair)),
        ("same_page_already_failed_in", len(failed)),
        ("repairs_available_offline",
         sum(1 for a in adjudications if a["repairable_offline"])),
        ("repairs_applied", sum(1 for a in adjudications if a["repaired_offline"])),
        ("owned_alternative_urls_found",
         sum(1 for a in adjudications if a["owned_alternative_url"]["exists"])),
        ("why_no_repair_was_applied",
         "one row (fairfield inn and suites grand rapids wyoming) has a "
         "canonical URL saved by the earlier Grand Rapids build, and it is the "
         "stable form of the SAME page the truncated route already redirects "
         "to. market_routing.apply_url_overlay refuses to displace a URL a lane "
         "can fetch, which is correct, so swapping it would repair nothing. "
         "Every other unresolved row either already reaches its own property "
         "page or needs a URL no artifact on this branch names."),
        ("by_verdict", OrderedDict(sorted(verdicts.items()))),
        ("saved_captures_still_on_disk",
         sum(1 for a in adjudications if a["saved_capture"])),
        ("brand_contradiction_scan", OrderedDict((
            ("routed_rows_scanned", sum(
                1 for e in routing_doc["entries"]
                if e.get("routing_state") == "ROUTED")),
            ("contradictions", len(brand_scan)),
            ("rows", brand_scan),
            ("why", "a row whose NAME is one chain and whose official_url is "
                    "another chain's domain is refuted by the two brands' own "
                    "authority. The check only ever refutes a route; it never "
                    "chooses one."),
        ))),
        ("finding",
         "seven of the eight ROUTING_REPAIR_REQUIRED rows are not routing "
         "defects. Their URLs already resolve to the property's own page and "
         "the page title names the property; what failed is corroboration -- "
         "the page prints no telephone, or the census address is corrupt, or "
         "the property was rebranded. A purchase changes none of that, and "
         "every declined capture is still on disk, so a founder ruling on "
         "identity costs nothing to act on."),
        ("adjudications", adjudications),
    )))

    # ------------------------------------------------------------------ #
    # Phase 3
    # ------------------------------------------------------------------ #
    # A clean row whose IDENTITY is one of the two open questions is withheld
    # from the candidate list even though its policy evidence is fine. Comfort
    # Suites Grandville is the case: the page answered, and whether that answer
    # belongs to one hotel or two is exactly what has not been decided.
    exception_keys = {r["identity_key"] for r in exceptions}
    hold_keys = {k for pair in NAMED_HOLDS for k in pair}
    withheld_on_identity = sorted(r["identity_key"] for r in clean
                                  if r["identity_key"] in hold_keys)
    candidates = [r for r in clean
                  if r["identity_key"] not in (exception_keys | hold_keys)]
    pet_friendly = [r for r in candidates
                    if r["classification"] == CLEAN_PET_FRIENDLY]
    no_pets = [r for r in candidates
               if r["classification"] == CLEAN_VERIFIED_NO_PETS]

    # ------------------------------------------------------------------ #
    # Phase 3, built AFTER the candidate list so "in_authority_candidates"
    # names membership of the list that actually exists rather than of the
    # clean rows it is derived from -- the two differ by exactly the row the
    # hold withholds, which is the one a reader most needs to be right.
    # ------------------------------------------------------------------ #
    candidate_keys = [r["identity_key"] for r in candidates]
    holds_019 = _header(
        "ptf-identity-hold-dossier/1.0",
        "The two identity questions this market has not answered, with the "
        "evidence that would settle each. Neither is merged, resolved or "
        "promoted here.",
        {k: paths[k] for k in ("dedup", "census", "routing")})
    holds_019.update(build_holds(census, dedup, routing, candidate_keys))

    # ------------------------------------------------------------------ #
    # Phase 4
    # ------------------------------------------------------------------ #
    unresolved = len(adjudications) + len(exceptions)
    authority_019 = _header(
        "ptf-proposed-authority-candidates/1.0",
        "What WOULD become this market's authority once the founder signs. It "
        "is a candidate list and not an authority: no decision, reviewer id or "
        "timestamp is written by this module, and this market's founder review "
        "has not run.",
        {k: paths[k] for k in ("replay", "store", "packet", "census")})
    authority_019.update(OrderedDict((
        ("is_an_authority", False),
        ("why_not", "market_proposed_authority_cli gates on the founder's "
                    "decision ledger -- only a row the founder SIGNED may "
                    "become authority -- and founder_review is NOT_RUN for "
                    "this market. Building one here would be a signature in "
                    "all but name."),
        ("binding_contract", BINDING_CONTRACT),
        ("registered_shard_baseline", shard_baseline()),
        ("counts", OrderedDict((
            ("census", int(census_doc.get("count") or len(census))),
            ("routed", sum(1 for e in routing_doc["entries"]
                           if e.get("routing_state") == "ROUTED")),
            ("reusable_evidence_processed", len(rows)),
            ("pet_friendly_candidates", len(pet_friendly)),
            ("verified_no_pets_candidates", len(no_pets)),
            ("hold_count", counts.get(HOLD_ALLOWANCE_NOT_STATED, 0)
             + counts.get(HOLD_SOURCE_SILENT_ON_PETS, 0)),
            ("policy_fact_corrections", counts.get(POLICY_FACT_CORRECTION, 0)),
            ("identity_review_count", counts.get(IDENTITY_CONFLICT, 0)),
            ("routing_unresolved", len(adjudications)),
            ("routing_repairs_completed",
             sum(1 for a in adjudications if a["repaired_offline"])),
            ("identity_holds", len(NAMED_HOLDS)),
            ("clean_but_withheld_on_an_open_identity",
             len(withheld_on_identity)),
            ("total_resolved", len(candidates)),
            ("total_unresolved", unresolved),
        ))),
        ("withheld_on_an_open_identity", withheld_on_identity),
        ("counts_reconcile", OrderedDict((
            ("reusable_rows", len(rows)),
            ("routing_rows_adjudicated", len(adjudications)),
            ("resolved", len(candidates)),
            ("unresolved", unresolved),
            ("withheld_on_identity", len(withheld_on_identity)),
            ("total", len(candidates) + unresolved + len(withheld_on_identity)),
            ("expected", len(rows) + len(adjudications)),
            ("ok", len(candidates) + unresolved + len(withheld_on_identity)
             == len(rows) + len(adjudications)),
            ("why", "every reusable row and every unresolved routed row lands "
                    "in exactly one of the three buckets, and none is invented "
                    "or dropped between them"),
        ))),
        ("candidates", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("proposed_class", r["classification"]),
            ("semantic_approval_hash", r["semantic_approval_hash"]),
            ("snapshot_hash", r["snapshot_hash"]),
            ("membrane_verdict", r["membrane_verdict"]),
            ("review_status", PENDING),
            ("founder_decision", ""),
        )) for r in candidates]),
    )))
    authority_019["validation"] = validate(
        candidates=candidates, rows=rows, adjudications=adjudications,
        replay=replay, store=store, holds=holds_019, census=census)

    return OrderedDict((
        ("exception_review_packet", packet_019),
        ("routing_repair", repair_019),
        ("identity_holds", holds_019),
        ("proposed_authority_candidates", authority_019),
    ))


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def validate(*, candidates: Sequence[Mapping], rows: Sequence[Mapping],
             adjudications: Sequence[Mapping], replay: Mapping,
             store: Mapping, holds: Mapping, census: Mapping) -> Dict:
    keys = [r["identity_key"] for r in candidates]
    urls = [r["source_url"] for r in rows
            if r["identity_key"] in set(keys) and r["source_url"]]
    duplicate_urls = sorted(u for u, n in Counter(urls).items() if n > 1)

    held = {k for pair in NAMED_HOLDS for k in pair}
    held_in_authority = sorted(held & set(keys))
    rejected = sorted(k for k in keys
                      if str((store.get(k, {}).get("membrane") or {})
                             .get("verdict") or "") != "VALID")
    unclassified = sorted(r["identity_key"] for r in rows
                          if r["classification"] not in ALL_CLASSES)
    unsigned = sorted(r["identity_key"] for r in candidates
                      if r["founder_decision"] or r["review_status"] != PENDING)
    unhashed = sorted(r["identity_key"] for r in candidates
                      if not r["semantic_approval_hash"])
    no_action = sorted(a["identity_key"] for a in adjudications
                       if not a["next_action"])

    payable = int(replay["counts"]["genuinely_payable_after_replay"])

    checks = OrderedDict((
        ("no_already_paid_page_is_reacquired", OrderedDict((
            ("ok", payable == 0),
            ("genuinely_payable_after_replay", payable),
            ("why", "the cross-run ledger suppressed the whole routed cohort in "
                    "018 and this pass bought nothing, so nothing can be "
                    "reacquired")))),
        ("no_duplicate_canonical_url_enters_twice", OrderedDict((
            ("ok", not duplicate_urls),
            ("duplicate_source_urls", duplicate_urls)))),
        ("no_shared_telephone_decides_identity", OrderedDict((
            ("ok", all(not h["decided_on_shared_telephone"]
                       and not h["merged_by_this_pass"]
                       for h in holds["holds"])),
            ("holds", holds["count"]),
            ("why", "018 removed phone-alone confirmation from the paid ledger, "
                    "and this pass decides no identity at all")))),
        ("no_held_identity_enters_authority", OrderedDict((
            ("ok", not held_in_authority),
            ("identity_keys", held_in_authority)))),
        ("no_membrane_rejected_observation_enters_authority", OrderedDict((
            ("ok", not rejected), ("identity_keys", rejected),
            ("why", "the proposed-authority builder does not consult the "
                    "membrane on its own, so the verdict is checked here "
                    "rather than assumed")))),
        ("every_reusable_row_is_classified_exactly_once", OrderedDict((
            ("ok", not unclassified and len(rows) == 54),
            ("rows", len(rows)), ("unclassified", unclassified)))),
        ("no_approval_is_written_by_this_pass", OrderedDict((
            ("ok", not unsigned), ("identity_keys", unsigned),
            ("why", "every candidate leaves here MACHINE_REVIEWED_PENDING_"
                    "OPERATOR with empty decision fields; an attestation needs "
                    "the human, not the field")))),
        ("every_candidate_binds_specific_evidence", OrderedDict((
            ("ok", not unhashed), ("without_a_semantic_hash", unhashed)))),
        ("every_unresolved_row_names_one_next_action", OrderedDict((
            ("ok", not no_action), ("without_an_action", no_action)))),
        ("spend_is_zero", OrderedDict((
            ("ok", True), ("usd", 0.0), ("plan_credits", 0.0),
            ("provider_calls", 0),
            ("why", "no provider is constructed; every input is an artifact on "
                    "this branch or a capture already saved on disk")))),
    ))
    checks["all_pass"] = all(v["ok"] for v in checks.values())
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(LP))
    args = parser.parse_args(argv)

    paths = {
        "replay": LP / "grand_rapids_holland_mi_cross_run_ledger_replay_018.json",
        "store": LP / "grand_rapids_holland_mi_observation_store_001.json",
        "packet": LP / "grand_rapids_holland_mi_founder_review_packet_001.json",
        "analysis": LP / "grand_rapids_holland_mi_founder_review_analysis_001.json",
        "closeout": LP / "grand_rapids_holland_mi_acquisition_merged_closeout_001.json",
        "census": (LP / "identity_census" / "recensus"
                   / "grand-rapids-holland-mi.json"),
        "prior_partition": LP / "grand_rapids_holland_final_partition_001.json",
        "dedup": LP / "grand_rapids_holland_mi_pre_acquisition_dedup_001.json",
        "routing": LP / "grand_rapids_holland_mi_routing_recovered_001.json",
    }
    documents = build(paths)
    out_dir = Path(args.out_dir)
    names = {
        "exception_review_packet":
            "grand_rapids_holland_mi_exception_review_packet_019.json",
        "routing_repair":
            "grand_rapids_holland_mi_routing_repair_019.json",
        "identity_holds":
            "grand_rapids_holland_mi_identity_holds_019.json",
        "proposed_authority_candidates":
            "grand_rapids_holland_mi_proposed_authority_candidates_019.json",
    }
    for slot, document in documents.items():
        _write(out_dir / names[slot], document)

    packet = documents["exception_review_packet"]
    repair = documents["routing_repair"]
    authority = documents["proposed_authority_candidates"]
    counts = authority["counts"]
    print("reusable processed  : %d" % counts["reusable_evidence_processed"])
    for name, value in packet["by_classification"].items():
        print("  %-28s %d" % (name.lower(), value))
    print("exceptions to read  : %d" % packet["exceptions_requiring_a_reading"])
    print("routing adjudicated : %d (repairs applied %d)"
          % (repair["rows_adjudicated"], repair["repairs_applied"]))
    for name, value in repair["by_verdict"].items():
        print("  %-40s %d" % (name.lower(), value))
    print("saved captures kept : %d of %d"
          % (repair["saved_captures_still_on_disk"], repair["rows_adjudicated"]))
    print("pet-friendly / no-pets: %d / %d"
          % (counts["pet_friendly_candidates"], counts["verified_no_pets_candidates"]))
    print("resolved / unresolved : %d / %d"
          % (counts["total_resolved"], counts["total_unresolved"]))
    print("identity holds        : %d" % counts["identity_holds"])
    print("validation            : %s" % authority["validation"]["all_pass"])
    for slot, name in names.items():
        print("written               : %s" % name)
    return 0 if authority["validation"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
