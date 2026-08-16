"""PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-002 -- close the Cleveland partition.

WHAT THIS WORK ORDER FOUND, AND WHY THIS MODULE EXISTS
------------------------------------------------------
The 002 work order asked for the Cleveland Work-browser package to be
integrated. It already was: all twenty-seven files in the handback hash
byte-identical to the hashes ``PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001``
recorded at commit ``6f9ba1d``, no new file arrived, and all 135 screenshot
directories are still empty. Re-running that integrator reproduces its
adjudication exactly -- 135/135 reconciled, zero duplicates, zero omissions,
one routing correction accepted and fourteen rejected, published 21 -> 21.
Re-adjudicating the same bytes into a second ledger would create the duplicate
evidence records the work order forbids.

What 002 asks for that did NOT exist is its requirement 11: *a complete final
partition of all 188 Cleveland census identities, every identity in exactly one
final state, and exactly one next action for every unresolved property.* Before
this module, Cleveland's closure was spread across three artifacts that nothing
joined:

  * ``hotel_policy_facts_cleveland-akron-canton-oh.json``  -- the 21 published
  * ``hotel_exclusions.json``                              -- the 8 verified no-pets
  * ``cleveland_unresolved_manifest.json``                 -- 159 unresolved

and ``build_market_manifest.build_package`` derives ``unresolved`` by
SUBTRACTION (``confirmed - published - no_pets``), so the pinned
``(188, 21, 8, 29, 159)`` reconciliation would pass unchanged even if the
unresolved manifest enumerated the wrong 159 hotels. The arithmetic was
guarded; the membership never was.

Joining them turned up two real defects, both fixed by this work order:

1. **The unresolved manifest disagreed with routing authority.** 6f9ba1d
   corrected Sonesta ES Suites Cleveland Airport to the Simply Suites path in
   ``identity_routing.json`` after the rebrand, but the unresolved manifest --
   which ``deploy/netlify/release_contracts/cleveland-akron-canton-oh.json``
   calls "this market's reconciliation of record" -- still carried the dead ES
   Suites URL and a next action pointing at it. Exactly one of the 143 routed
   unresolved identities drifted; the other 142 agreed. Propagated here, and
   ``test_cleveland_final_partition_002`` now asserts the agreement standing.

2. **A sixteenth routing proposal was never adjudicated.** Sixteen rows carry a
   populated proposed replacement URL, not fifteen. The extra one is Hyatt Place
   Cleveland/Westlake/Crocker Park, and it was missed for a structural reason
   worth recording: batch 2 was completed separately and uses a different
   24-column schema. 001 keyed routing adjudication on the classification
   ``ROUTING_CORRECTION_PROPOSED``, but this row's ``final_classification`` is
   ``EVIDENCE_SUCCESS_OFFICIAL_ROUTE_RECOVERED`` and the routing flag lives in a
   differently-named column reading ``ROUTING_REVIEW_NEEDED_NOT_AUTHORITY``. The
   operator had explicitly asked for routing review and the adjudicator never
   saw the request.

   The substance matters too: the recorded vanity domain
   ``hyattplaceclevelandwestlake.com`` returned 502 Bad Gateway, and the
   proposal is Hyatt's own brand route, which displayed a name, address and
   phone all agreeing with the census. It is still HELD rather than accepted.
   hyatt.com is bot-walled, so no first-party probe may confirm the destination
   (ADR-PTF-AUTOMATED-BROWSING); the property code ``clezc`` appears only in the
   proposed URL's path and the page displayed none; and the operator's own row
   says it is not authority. PTF-COLUMBUS-HYATT-002 established the lawful path
   -- an operator screenshot of the property's own page -- and that is its one
   next action.

FINAL STATES ARE BLOCKERS, NOT VERDICTS
---------------------------------------
"Exactly one next action" is only meaningful if the state says what the
identity is waiting ON. So the closed set below names blockers, and each
unresolved identity's next action is carried VERBATIM from the authority that
last examined it -- 001's ledger for the 135 it reviewed, the unresolved
manifest for the 24 it did not. No next-action prose is invented here.

That coarsening is a crosswalk, not a re-adjudication, and it does not always
agree with 001's outcome buckets. The three properties 001 filed under
``ACCESS_BLOCKED`` because a proposed DESTINATION refused to render are waiting
on a routing replacement (their own next actions say "recover the property URL
and re-propose"), so they land in ``AWAITING_ROUTING_REPLACEMENT`` while
``ACCESS_BLOCKED`` keeps only the two identities with no lawful automated path
at all. Every item carries its upstream ``work_browser_outcome`` and
``unresolved_manifest_classification``, so the crosswalk is auditable in both
directions and ``CROSSWALK_NOTES`` records each deliberate divergence.

WHAT THIS MODULE DOES NOT DO
----------------------------
It publishes nothing, excludes nothing, and writes no routing record. The
package is still a transcription with no artifact of any source surface, so
every determination 001 reached on that basis stands unchanged. Cleveland stays
188 confirmed / 21 published / 8 no-pets / 29 resolved / 159 unresolved.

Run:  python -m scripts.pettripfinder.cleveland_final_partition_002 [--apply]
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts.identity_key import (            # noqa: E402
    ptf_identity_key,
)
from scripts.pettripfinder.identity_routing import registrable_domain   # noqa: E402
from scripts.pettripfinder.site_data import normalize_name              # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-002"
RUN_ID = "cleveland-final-partition-002"
AS_OF = "2026-08-12"
REVIEWER = "jfields80"
SCHEMA = "ptf-market-final-partition/1.1"

_LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = _LP / "identity_census" / ("%s.json" % MARKET)
FACTS_PATH = _LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = _LP / "hotel_exclusions.json"
ROUTING_PATH = _LP / "identity_routing.json"
UNRESOLVED_PATH = _LP / "cleveland_unresolved_manifest.json"
WORK_BROWSER_PATH = _LP / "cleveland_work_browser_pass_001.json"
PARTITION_PATH = _LP / ("cleveland_final_partition_002.json")

#: Screenshots are the artifact class every publication route requires. Untracked
#: by design (``data/`` is gitignored), so absence is "unknown", never "zero".
SCREENSHOT_DIR = (_REPO_ROOT / "data" / "operator_evidence"
                  / "cleveland-founder-review-001" / "screenshots")

# --------------------------------------------------------------------------
# The closed final-state set. Two terminal states, ten blockers.
# --------------------------------------------------------------------------

PUBLISHED_PET_FRIENDLY = "PUBLISHED_PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"

AWAITING_POLICY_ARTIFACT = "AWAITING_POLICY_ARTIFACT"
AWAITING_POLICY_OBSERVATION = "AWAITING_POLICY_OBSERVATION"
AWAITING_ATTENDED_CAPTURE = "AWAITING_ATTENDED_CAPTURE"
AWAITING_ROUTING_REPLACEMENT = "AWAITING_ROUTING_REPLACEMENT"
AWAITING_ROUTING_REVIEW = "AWAITING_ROUTING_REVIEW"
AWAITING_OFFICIAL_URL = "AWAITING_OFFICIAL_URL"
AWAITING_PROPERTY_LEVEL_URL = "AWAITING_PROPERTY_LEVEL_URL"
AWAITING_CONTRADICTION_RESOLUTION = "AWAITING_CONTRADICTION_RESOLUTION"
AWAITING_CENSUS_REVIEW = "AWAITING_CENSUS_REVIEW"
ACCESS_BLOCKED = "ACCESS_BLOCKED"

TERMINAL_STATES: Tuple[str, ...] = (PUBLISHED_PET_FRIENDLY, VERIFIED_NO_PETS)

UNRESOLVED_STATES: Tuple[str, ...] = (
    AWAITING_POLICY_ARTIFACT,
    AWAITING_POLICY_OBSERVATION,
    AWAITING_ATTENDED_CAPTURE,
    AWAITING_ROUTING_REPLACEMENT,
    AWAITING_ROUTING_REVIEW,
    AWAITING_OFFICIAL_URL,
    AWAITING_PROPERTY_LEVEL_URL,
    AWAITING_CONTRADICTION_RESOLUTION,
    AWAITING_CENSUS_REVIEW,
    ACCESS_BLOCKED,
)

FINAL_STATES: Tuple[str, ...] = TERMINAL_STATES + UNRESOLVED_STATES

STATE_MEANINGS: Dict[str, str] = {
    PUBLISHED_PET_FRIENDLY:
        "A pet policy passed the membrane and the publication guard on this "
        "property's own captured page, and the hotel has a public route.",
    VERIFIED_NO_PETS:
        "A refusal was captured with a citable artifact and source_hash; the "
        "property is excluded and generates no route.",
    AWAITING_POLICY_ARTIFACT:
        "The policy WORDING is known but no artifact of the surface it was read "
        "from exists. Every publication route requires a sha256 of the page (or "
        "of an operator screenshot of the page); a hash of a transcription binds "
        "the typing, not the page.",
    AWAITING_POLICY_OBSERVATION:
        "The route is sound and the page served its content, but no pet policy "
        "has ever been observed on it. UNKNOWN, never a refusal.",
    AWAITING_ATTENDED_CAPTURE:
        "The policy exists on the property's own surface but behind a click, an "
        "accordion, a modal, or client-side rendering that a static fetch cannot "
        "reach. An attended browser is the lawful route, not a bypass.",
    AWAITING_ROUTING_REPLACEMENT:
        "The URL on record is provably not this property's page -- dead, a "
        "different business, or a brand surface that refused to serve it. Policy "
        "work cannot start until the route is replaced.",
    AWAITING_ROUTING_REVIEW:
        "A routing proposal exists whose destination cannot be confirmed "
        "first-party because the brand is bot-walled. It is HELD: neither "
        "accepted on a transcription's word nor discarded.",
    AWAITING_OFFICIAL_URL:
        "No official URL has ever been found for this identity. The census "
        "confirms the property exists; nothing says where its page is.",
    AWAITING_PROPERTY_LEVEL_URL:
        "Only a brand index, brand-locator, or city-level URL is bound. Such a "
        "URL is property-specific for nobody and cannot back a policy fact.",
    AWAITING_CONTRADICTION_RESOLUTION:
        "The evidence conflicts with itself. M8 forbids this layer from picking "
        "a winner; both surfaces must be captured for approval_resolution.",
    AWAITING_CENSUS_REVIEW:
        "The queued identity itself is in question -- not lodging, or rebranded "
        "so that the name and phone on record are stale. Census work, not "
        "policy work.",
    ACCESS_BLOCKED:
        "An anti-bot or access-control wall stands between us and the "
        "property's own page and there is no lawful automated path. Never "
        "retried programmatically, never bypassed.",
}

# --------------------------------------------------------------------------
# Crosswalk: 001's per-row outcome/reason_code -> this partition's blocker.
# --------------------------------------------------------------------------

#: Keyed on 001's ``reason_code``, which is finer-grained than its ``outcome``
#: and is what actually determines the blocker.
REASON_CODE_TO_STATE: Dict[str, str] = {
    "AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": AWAITING_POLICY_ARTIFACT,
    "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": AWAITING_POLICY_ARTIFACT,
    "PAGE_RENDERED_NO_PET_POLICY_STATED": AWAITING_POLICY_OBSERVATION,
    "ROUTING_CORRECTION_ACCEPTED": AWAITING_POLICY_OBSERVATION,
    "FAQ_QUESTION_RENDERED_WITHOUT_ITS_ANSWER": AWAITING_ATTENDED_CAPTURE,
    "JS_RENDERED_BLANK_CONTENT": AWAITING_ATTENDED_CAPTURE,
    "POLICY_MODAL_BLANK": AWAITING_ATTENDED_CAPTURE,
    "OFFICIAL_URL_RETURNS_404": AWAITING_ROUTING_REPLACEMENT,
    "ROUTING_DESTINATION_REFUSED_TO_RENDER": AWAITING_ROUTING_REPLACEMENT,
    "PAGE_STATES_BOTH_PET_FRIENDLY_AND_NO_PETS": AWAITING_CONTRADICTION_RESOLUTION,
    "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION": AWAITING_CONTRADICTION_RESOLUTION,
    "QUEUED_IDENTITY_IS_NOT_LODGING": AWAITING_CENSUS_REVIEW,
    "ANTI_BOT_CHALLENGE": ACCESS_BLOCKED,
}

#: Two reason codes cover rows whose blocker genuinely differs per property, so
#: the reason code alone cannot decide them. Each entry states why, and each is
#: taken from what 001's own next action for that row asks for -- no new
#: judgement about the property is introduced here.
PER_SLUG_STATE: Dict[str, Tuple[str, str]] = {
    # reason_code ROUTED_URL_RESOLVES_TO_A_DIFFERENT_BUSINESS: two need a new
    # URL, one needs the census to decide whether it is lodging at all.
    "embassy-suites-by-hilton-akron-canton-airport": (
        AWAITING_ROUTING_REPLACEMENT,
        "The record routes to the on-site bar (luggageroomspeakeasy.com); the "
        "next action is to replace it with the Hilton property page."),
    "the-bertram-inn-at-glenmoor": (
        AWAITING_ROUTING_REPLACEMENT,
        "Both the recorded /Spa path and the rejected proposal point at the "
        "spa; the lodging page on glenmoorcc.com still has to be found."),
    "the-rowley-inn": (
        AWAITING_CENSUS_REVIEW,
        "The page presents a restaurant and bar. Whether this is lodging "
        "inventory at all is a census question, and answering it wrongly puts "
        "a restaurant in a hotel directory."),
    # reason_code ROUTING_CORRECTION_REJECTED_NO_VALID_REPLACEMENT: the
    # proposal failed, so the blocker is whatever the RECORDED route leaves.
    "crowne-plaza-cleveland-airport": (
        AWAITING_ROUTING_REPLACEMENT,
        "crowneplazacle.com returns 502; a working IHG endpoint is needed."),
    "days-inn-richfield": (
        AWAITING_ROUTING_REPLACEMENT,
        "The proposal was a brand search page; the property page must be "
        "re-resolved from the Wyndham locator."),
    "highlander-inn": (
        AWAITING_ROUTING_REPLACEMENT,
        "highlanderinncle.com returns 502; either a working endpoint or an "
        "honest NO_OFFICIAL_URL record is needed."),
    "sonesta-es-suites-cleveland-westlake": (
        AWAITING_ROUTING_REPLACEMENT,
        "The proposal was Sonesta's Westlake CITY page; the property page for "
        "30100 Clemens Rd still has to be resolved."),
    "springhill-suites-solon": (
        AWAITING_ROUTING_REPLACEMENT,
        "The springhillsolon.com vanity domain is dead; the Marriott property "
        "page replaces it."),
    "economy-inn": (
        AWAITING_ATTENDED_CAPTURE,
        "No routing action -- the '#/' proposal was the same resource. The "
        "site renders client-side, so the existing URL needs an attended "
        "capture."),
    "the-bertram-hotel-conference-center": (
        AWAITING_POLICY_OBSERVATION,
        "No routing action -- the proposal only dropped 'www.'. The page "
        "rendered and stated no pet policy, so the policy is simply "
        "unobserved."),
    "studio-6-extended-stay-hotel-mentor": (
        AWAITING_CENSUS_REVIEW,
        "The address matches but the phone and brand do not: Studio 6 appears "
        "to have rebranded to Suburban Studios, so the census identity is "
        "stale and must be refreshed before any capture is trusted."),
    # The sixteenth routing proposal, unadjudicated until this work order. Its
    # policy transcription was read from the PROPOSED hyatt.com page, not from
    # the URL on record, so the transcription is not attached to a verified
    # route and routing is the blocker that comes first.
    "hyatt-place-cleveland-westlake-crocker-park": (
        AWAITING_ROUTING_REVIEW,
        "Sixteenth routing proposal. It is a batch-2 row, and batch 2 uses a "
        "different 24-column schema whose routing field reads "
        "ROUTING_REVIEW_NEEDED_NOT_AUTHORITY while its classification reads "
        "EVIDENCE_SUCCESS_OFFICIAL_ROUTE_RECOVERED -- so keying adjudication on "
        "the classification ROUTING_CORRECTION_PROPOSED, as 001 did, skipped a "
        "row the operator had explicitly flagged for routing review. The "
        "recorded vanity domain returned 502 Bad Gateway and the proposal is "
        "Hyatt's own brand route; street key (2020|crocker|44145) and phone "
        "both agree with the census. It is still HELD: hyatt.com is bot-walled, "
        "so the destination may not be probed first-party "
        "(ADR-PTF-AUTOMATED-BROWSING), the property code clezc appears only in "
        "the proposed URL's path and the page displayed none "
        "(property_code_status WITHHELD_NOT_DISPLAYED), and the operator's own "
        "row says it is not authority. That leaves the transcription this "
        "package could not substantiate anywhere else."),
}

#: Why a given 001 outcome bucket splits here, keyed by that outcome. The
#: NUMBERS are never written down -- ``build_partition`` derives the actual
#: outcome -> state distribution from the items, so a hand-counted total can
#: never go stale against the data. These entries supply only the reason.
CROSSWALK_WHY: Dict[str, str] = {
    "ACCESS_BLOCKED":
        "001 filed a row as ACCESS_BLOCKED whenever the surface it reached "
        "refused to render -- including when that surface was a PROPOSED "
        "destination rather than the property's own route. Comfort Suites "
        "Hartville, InterContinental Suites Cleveland and Extended Stay America "
        "Premier Suites are all waiting on a routing replacement; their own "
        "next actions say 'recover the property URL' and 're-propose'. "
        "ACCESS_BLOCKED here keeps only identities with no lawful automated "
        "path to the property's own page at all.",
    "MANUAL_VERIFICATION_REQUIRED":
        "'A human must look' is not a blocker -- it is true of every unresolved "
        "row. Split by what the human is actually being asked to do: settle "
        "conflicting evidence, find a working URL, or decide whether the "
        "identity belongs in a hotel census.",
    "OTHER_UNRESOLVED":
        "The eight rejected routing proposals leave different blockers behind, "
        "because a rejected proposal returns the identity to whatever its "
        "RECORDED route already left unanswered. Two of 001's own next actions "
        "for them open with 'No routing action'.",
    "EVIDENCE_CANDIDATE_AWAITING_ACCEPTED_ARTIFACT":
        "Hyatt Place Cleveland/Westlake/Crocker Park carries the sixteenth, "
        "unadjudicated routing proposal, and its transcription was read from "
        "the proposed page rather than from the route on record -- so routing "
        "is the question that comes first for it.",
    "IDENTITY_ONLY":
        "A page that rendered and stated no pet policy is waiting on an "
        "observation, not on an artifact. UNKNOWN, never a refusal.",
    "SELECTOR_OR_SURFACE_GAP":
        "An IHG FAQ question with no answer, a blank policy modal and a "
        "client-side-rendered page are one blocker: the words exist on the "
        "property's own surface and a static fetch cannot reach them.",
    "CONTRADICTION":
        "Kept whole. M8 forbids this layer from preferring one half of "
        "conflicting evidence.",
    "IDENTITY_OR_ROUTING_CORRECTED_POLICY_UNRESOLVED":
        "Routing is not publication. The corrected route means the next capture "
        "has somewhere real to look, and the pet policy is still unobserved.",
}

#: The ONE next action this work order authors rather than carries.
#:
#: Everywhere else the action is copied verbatim from the authority that last
#: examined the property. This row is the exception because 001 never examined
#: the question that blocks it: it adjudicated the row's POLICY and wrote a
#: policy action, and its routing proposal was never seen. Carrying that policy
#: action forward would leave a routing-blocked identity pointed at a capture it
#: cannot lawfully make.
PER_SLUG_NEXT_ACTION: Dict[str, str] = {
    "hyatt-place-cleveland-westlake-crocker-park":
        "Supply an operator screenshot of the proposed Hyatt brand page "
        "(clezc) showing the property name, street address and phone, so the "
        "routing correction can be accepted on a stored artifact the way "
        "PTF-COLUMBUS-HYATT-002 accepted Hyatt evidence -- the recorded vanity "
        "domain returns 502 and hyatt.com must not be automated.",
}
AUTHORED_HERE = "ptf_cleveland_work_browser_integration_002"

#: The unresolved manifest's classifications, for the 24 identities the
#: Work-browser pass never reviewed.
MANIFEST_CLASSIFICATION_TO_STATE: Dict[str, str] = {
    "NO_OFFICIAL_URL": AWAITING_OFFICIAL_URL,
    "IDENTITY_SOURCE_RECOVERY": AWAITING_PROPERTY_LEVEL_URL,
    "URL_SHAPE_NOT_PROPERTY": AWAITING_PROPERTY_LEVEL_URL,
    "ADR_ACCESS_BLOCKED": ACCESS_BLOCKED,
    "ADAPTER_GAP_INDEPENDENT": AWAITING_POLICY_OBSERVATION,
    "ROUTED_AWAITING_CAPTURE": AWAITING_POLICY_OBSERVATION,
    "ROUTED_NO_BRAND_ADAPTER": AWAITING_POLICY_OBSERVATION,
    "SELECTOR_OR_SURFACE_GAP": AWAITING_ATTENDED_CAPTURE,
}

#: The one routing correction 6f9ba1d applied that never reached the unresolved
#: manifest. Propagated by ``--apply``.
SONESTA_KEY = "sonesta es suites cleveland airport"
SONESTA_MANIFEST_FIX = {
    "why_unresolved":
        "no_adapter_for_brand:sonesta. The official URL was corrected at "
        "PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 after Sonesta rebranded "
        "this property from ES Suites to Simply Suites; the census identity is "
        "unchanged and the pet policy is still unobserved.",
    "next_action":
        "Independent property with no chain adapter. Open the corrected Simply "
        "Suites URL and screenshot the pet policy plus the page area showing "
        "name/address.",
}


class PartitionError(RuntimeError):
    """The partition is not a partition. Never downgraded to a warning."""


def _json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: Mapping) -> None:
    """LF endings always. A CRLF rewrite would make every raw sha256 of this
    file disagree with the blob git stores (PTF-PROMOTION-002)."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def _sonesta_url_from_routing(routes, facts_hotels=None) -> str:
    for record in routes:
        if record["hotel_ref"]["normalized_name"] == SONESTA_KEY:
            return record["official_property_url"]
    # A published identity may not hold a routing record (the standing
    # invariant), so once Sonesta publishes, its URL authority is the
    # published record itself -- the same URL the retired route carried.
    for hotel in facts_hotels or []:
        if hotel.get("identity_key") == SONESTA_KEY:
            return hotel["source_url"]
    raise PartitionError("no routing record for %r" % SONESTA_KEY)


# --------------------------------------------------------------------------
# Collision audits. Scoped the way PTF-CLEVELAND-MARKET-FACTORY-001 proved
# they must be: URLs globally, property codes within a registrable domain.
# --------------------------------------------------------------------------

def collision_audit(routes) -> Dict[str, object]:
    urls: Dict[str, List[str]] = {}
    codes: Dict[Tuple[str, str], List[str]] = {}
    slugs: Dict[str, List[str]] = {}
    for record in routes:
        key = record["hotel_ref"]["normalized_name"]
        url = (record.get("official_property_url") or "").strip().lower().rstrip("/")
        if url:
            urls.setdefault(url, []).append(key)
        code = (record.get("property_code") or "").strip().lower()
        if code:
            codes.setdefault((registrable_domain(url), code), []).append(key)
        slugs.setdefault(record["routing_id"], []).append(key)
    return {
        "url_reuse": {u: sorted(set(k)) for u, k in urls.items() if len(set(k)) > 1},
        "property_code_reuse_within_domain": {
            "%s|%s" % (d, c): sorted(set(k))
            for (d, c), k in codes.items() if len(set(k)) > 1},
        "routing_id_reuse": {r: sorted(set(k))
                             for r, k in slugs.items() if len(set(k)) > 1},
        "property_codes_shared_across_domains": {
            c: sorted({d for (d, cc) in codes if cc == c})
            for c in {cc for (_d, cc) in codes}
            if len({d for (d, cc) in codes if cc == c}) > 1},
    }


def screenshot_census() -> Dict[str, object]:
    """Image BYTES, never directory count. An empty directory is not evidence."""
    if not SCREENSHOT_DIR.exists():
        return {"scanned": False, "reason": "screenshot tree is gitignored and "
                                            "absent from this worktree",
                "image_files": None, "directories": None}
    dirs = [p for p in SCREENSHOT_DIR.iterdir() if p.is_dir()]
    images = [p for p in SCREENSHOT_DIR.rglob("*")
              if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    return {"scanned": True, "directories": len(dirs), "image_files": len(images),
            "reason": "" if images else
                      "every directory is empty; no artifact class exists here"}


# --------------------------------------------------------------------------
# The partition
# --------------------------------------------------------------------------

def build_partition() -> Dict:
    census = _json(CENSUS_PATH)
    facts = _json(FACTS_PATH)
    exclusions = _json(EXCLUSIONS_PATH)["exclusions"]
    routing_doc = _json(ROUTING_PATH)
    unresolved = _json(UNRESOLVED_PATH)
    work_browser = _json(WORK_BROWSER_PATH)

    if census["market_id"] != MARKET:
        raise PartitionError("census is for %r" % census["market_id"])

    by_key = OrderedDict((h["normalized_name"], h) for h in census["hotels"])
    if len(by_key) != len(census["hotels"]):
        raise PartitionError("census has duplicate normalized names")

    published = {h["key"] for h in facts["hotels"]}
    no_pets = {normalize_name(e["canonical_name"]) for e in exclusions
               if e.get("market_id") == MARKET
               and e["exclusion_state"] == "VERIFIED_NO_PETS"}
    market_routes = [r for r in routing_doc["routes"] if r.get("market_id") == MARKET]
    routes = {r["hotel_ref"]["normalized_name"]: r for r in market_routes}
    unres = {i["normalized_name"]: i for i in unresolved["items"]}
    wb = {i["normalized_name"]: i for i in work_browser["items"]}

    for label, keys in (("published", published), ("verified no-pets", no_pets),
                        ("unresolved manifest", set(unres)),
                        ("work-browser ledger", set(wb))):
        stray = sorted(keys - set(by_key))
        if stray:
            raise PartitionError("%s carries identities absent from the census: %s"
                                 % (label, stray))
    overlap = published & no_pets
    if overlap:
        raise PartitionError("published and excluded at once: %s" % sorted(overlap))

    # A per-slug override that matches nothing is a silent no-op, which is how a
    # typo becomes a wrong final state. Both tables must be fully consumed.
    used_state_overrides: List[str] = []
    used_action_overrides: List[str] = []

    items: List[Dict] = []
    for key, hotel in by_key.items():
        wb_item = wb.get(key)
        un_item = unres.get(key)
        route = routes.get(key)

        if key in published:
            state, source, action, why = PUBLISHED_PET_FRIENDLY, "hotel_policy_facts", "", ""
        elif key in no_pets:
            state, source, action, why = VERIFIED_NO_PETS, "hotel_exclusions", "", ""
        elif wb_item is not None:
            source = "cleveland_work_browser_pass_001"
            action = wb_item["next_action"]
            override = PER_SLUG_STATE.get(wb_item["slug"])
            if override is not None:
                state, why = override
                used_state_overrides.append(wb_item["slug"])
            else:
                reason = wb_item.get("reason_code")
                if reason not in REASON_CODE_TO_STATE:
                    raise PartitionError(
                        "no state mapping for reason_code %r (%s)" % (reason, key))
                state = REASON_CODE_TO_STATE[reason]
                why = ""
        elif un_item is not None:
            source = "cleveland_unresolved_manifest"
            action = un_item["next_action"]
            classification = un_item["classification"]
            if classification not in MANIFEST_CLASSIFICATION_TO_STATE:
                raise PartitionError("no state mapping for classification %r (%s)"
                                     % (classification, key))
            state = MANIFEST_CLASSIFICATION_TO_STATE[classification]
            why = ""
        else:
            raise PartitionError(
                "%r is in the census but in no authority: not published, not "
                "excluded, and in neither the unresolved manifest nor the "
                "Work-browser ledger" % key)

        authored = PER_SLUG_NEXT_ACTION.get(hotel["slug"])
        if authored is not None and state not in TERMINAL_STATES:
            action, source = authored, AUTHORED_HERE
            used_action_overrides.append(hotel["slug"])

        if state in TERMINAL_STATES and action:
            raise PartitionError("%s is terminal but carries a next action" % key)
        if state not in TERMINAL_STATES and not action.strip():
            raise PartitionError("%s is unresolved with no next action" % key)

        item = OrderedDict((
            # PTF-CENSUS-PARTITION-NORMALIZATION-001. The canonical join key
            # leads, because membership against a census is now a set
            # operation rather than a comparison between two normalisers that
            # spell "&" and "I-70" differently.
            ("identity_key", ptf_identity_key(hotel["canonical_name"])),
            ("normalized_name", key),
            ("canonical_name", hotel["canonical_name"]),
            ("slug", hotel["slug"]),
            ("city", hotel["city"]),
            ("postal_code", hotel["postal_code"]),
            ("final_state", state),
            ("resolved", state in TERMINAL_STATES),
            ("next_action", action),
            ("next_action_source", source),
            ("state_override_reason", why),
            ("official_url", (route or {}).get("official_property_url", "")),
            ("routing_binding_method", (route or {}).get("binding_method", "")),
            ("reviewed_in_work_browser_pass_001", wb_item is not None),
            ("work_browser_outcome", (wb_item or {}).get("outcome", "")),
            ("work_browser_reason_code", (wb_item or {}).get("reason_code", "")),
            ("policy_wording_shape", (wb_item or {}).get("policy_wording_shape", "")),
            ("unresolved_manifest_classification",
             (un_item or {}).get("classification", "")),
            # Which work order set this state, and when it was last reviewed.
            # An unresolved identity that nobody can attribute is a queue item
            # with no owner.
            ("determined_by", "" if state in TERMINAL_STATES else WORK_ORDER),
            ("updated_at", AS_OF),
        ))
        items.append(item)

    if sorted(used_state_overrides) != sorted(PER_SLUG_STATE):
        raise PartitionError(
            "per-slug state override(s) matched nothing: %s"
            % sorted(set(PER_SLUG_STATE) - set(used_state_overrides)))
    if sorted(used_action_overrides) != sorted(PER_SLUG_NEXT_ACTION):
        raise PartitionError(
            "per-slug next-action override(s) matched nothing: %s"
            % sorted(set(PER_SLUG_NEXT_ACTION) - set(used_action_overrides)))

    counts: Dict[str, int] = OrderedDict((s, 0) for s in FINAL_STATES)
    for item in items:
        counts[item["final_state"]] += 1

    # The 001-outcome -> final-state crosswalk, derived from the items so it can
    # never disagree with them. Only the prose reason is authored by hand.
    crosswalk: Dict[str, Dict] = OrderedDict()
    for item in items:
        outcome = item["work_browser_outcome"]
        if not outcome:
            continue
        row = crosswalk.setdefault(outcome, OrderedDict((
            ("rows", 0), ("final_states", OrderedDict()), ("why", ""))))
        row["rows"] += 1
        row["final_states"][item["final_state"]] = (
            row["final_states"].get(item["final_state"], 0) + 1)
    for outcome, row in crosswalk.items():
        row["final_states"] = OrderedDict(sorted(row["final_states"].items()))
        row["why"] = CROSSWALK_WHY.get(outcome, "")
        row["splits"] = len(row["final_states"]) > 1
    crosswalk = OrderedDict(sorted(crosswalk.items()))
    unexplained = sorted(o for o, r in crosswalk.items() if r["splits"] and not r["why"])
    if unexplained:
        raise PartitionError("outcome(s) split with no recorded reason: %s"
                             % unexplained)

    resolved = counts[PUBLISHED_PET_FRIENDLY] + counts[VERIFIED_NO_PETS]
    unresolved_total = sum(counts[s] for s in UNRESOLVED_STATES)
    if len(items) != census["count"]:
        raise PartitionError("partition covers %d of %d census identities"
                             % (len(items), census["count"]))
    if resolved + unresolved_total != census["count"]:
        raise PartitionError("states do not sum to the census")

    # The membership guarantee build_package's subtraction cannot give.
    derived_unresolved = set(by_key) - published - no_pets
    if derived_unresolved != set(unres):
        raise PartitionError(
            "the unresolved manifest is not census minus resolved: "
            "missing=%s extra=%s" % (sorted(derived_unresolved - set(unres)),
                                     sorted(set(unres) - derived_unresolved)))

    sonesta_routed = _sonesta_url_from_routing(market_routes,
                                               facts.get("hotels"))
    url_drift = sorted(
        [{"normalized_name": key,
          "unresolved_manifest": (item.get("official_url") or "").strip(),
          "identity_routing": routes[key]["official_property_url"]}
         for key, item in unres.items()
         if key in routes
         and (item.get("official_url") or "").strip()
         and (item.get("official_url") or "").strip()
         != routes[key]["official_property_url"]],
        key=lambda d: d["normalized_name"])

    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("run_id", RUN_ID),
        ("as_of", AS_OF),
        ("reviewer_id", REVIEWER),
        ("market_id", MARKET),
        ("note",
         "A complete final partition of this market's confirmed identity "
         "census: every identity in exactly one final state, and exactly one "
         "next action for every identity that is not terminal. Final states "
         "are BLOCKERS -- what the identity is waiting on -- not verdicts about "
         "the property. Nothing here publishes, excludes, or routes anything; "
         "it joins committed authority and states what remains. An unresolved "
         "identity is UNKNOWN and never a refusal."),
        ("inputs", OrderedDict((
            ("identity_census", str(CENSUS_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
            ("published_facts", str(FACTS_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
            ("exclusions", str(EXCLUSIONS_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
            ("identity_routing", str(ROUTING_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
            ("unresolved_manifest", str(UNRESOLVED_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
            ("work_browser_ledger", str(WORK_BROWSER_PATH.relative_to(_REPO_ROOT)).replace("\\", "/")),
        ))),
        ("evidence_determination", OrderedDict((
            ("work_browser_package_artifact_class", "OPERATOR_TRANSCRIBED_BROWSER_REVIEW"),
            ("publishable_without_a_page_artifact", False),
            ("screenshot_census", screenshot_census()),
            ("restated_from",
             "PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 (6f9ba1d). The "
             "handback's twenty-seven files hash byte-identical to the hashes "
             "that commit recorded, so its determination is carried forward "
             "unchanged rather than re-derived into a second ledger."),
        ))),
        ("reconciliation", OrderedDict((
            ("confirmed_identities", census["count"]),
            ("published_pet_friendly", counts[PUBLISHED_PET_FRIENDLY]),
            ("verified_no_pets", counts[VERIFIED_NO_PETS]),
            ("resolved", resolved),
            ("unresolved", unresolved_total),
            ("reviewed_in_work_browser_pass_001",
             sum(1 for i in items if i["reviewed_in_work_browser_pass_001"])),
            ("never_reviewed_by_any_browser_pass",
             sum(1 for i in items if not i["reviewed_in_work_browser_pass_001"]
                 and not i["resolved"])),
        ))),
        ("final_state_counts", counts),
        ("final_state_meanings", STATE_MEANINGS),
        ("crosswalk_from_pass_001_outcomes", crosswalk),
        ("authority_agreement", OrderedDict((
            ("unresolved_manifest_vs_identity_routing_url_drift", url_drift),
            ("sonesta_es_suites_cleveland_airport_routed_url", sonesta_routed),
        ))),
        ("collision_audit", collision_audit(routing_doc["routes"])),
        ("routing_proposals_in_package", OrderedDict((
            ("rows_carrying_a_proposed_replacement_url", 16),
            ("adjudicated_by_001", 15),
            ("accepted_by_001", 1),
            ("rejected_by_001", 14),
            ("missed_by_001_and_held_here", 1),
            ("accepted_by_002", 0),
            ("note",
             "The package manifest counts routing proposals by CLASSIFICATION "
             "and reports 14 (+1 in batch 2). Sixteen rows actually carry a "
             "populated proposed replacement URL. The sixteenth is Hyatt Place "
             "Cleveland/Westlake/Crocker Park, a batch-2 row whose "
             "routing_correction_status is ROUTING_REVIEW_NEEDED_NOT_AUTHORITY "
             "but whose final_classification is "
             "EVIDENCE_SUCCESS_OFFICIAL_ROUTE_RECOVERED, so a "
             "classification-keyed adjudication never saw it. HELD as "
             "AWAITING_ROUTING_REVIEW: hyatt.com may not be probed, so no "
             "first-party confirmation of the destination is available."),
        ))),
        ("items", items),
    ))


def apply_unresolved_manifest_fix() -> Optional[Dict[str, str]]:
    """Propagate 6f9ba1d's accepted routing correction into the manifest.

    Returns the before/after URLs, or ``None`` if the manifest already agrees.
    """
    doc = _json(UNRESOLVED_PATH)
    routed = _sonesta_url_from_routing(
        [r for r in _json(ROUTING_PATH)["routes"] if r.get("market_id") == MARKET])
    for item in doc["items"]:
        if item["normalized_name"] != SONESTA_KEY:
            continue
        before = item.get("official_url", "")
        if before == routed:
            return None
        item["official_url"] = routed
        item["why_unresolved"] = SONESTA_MANIFEST_FIX["why_unresolved"]
        item["next_action"] = SONESTA_MANIFEST_FIX["next_action"]
        # The reconciliation of record has to say when it was last touched, and
        # by what. Counts are unchanged -- this corrects a URL, not a state.
        doc["as_of"] = AS_OF
        doc.setdefault("corrections", []).append(OrderedDict((
            ("work_order", WORK_ORDER),
            ("as_of", AS_OF),
            ("normalized_name", SONESTA_KEY),
            ("field", "official_url"),
            ("before", before),
            ("after", routed),
            ("why",
             "PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 (6f9ba1d) corrected "
             "this property's route in identity_routing.json after Sonesta's "
             "ES Suites -> Simply Suites rebrand, but the correction never "
             "reached this manifest, so the reconciliation of record and "
             "routing authority disagreed on one URL and this next action "
             "pointed at a superseded path. No count changes: the identity "
             "is unresolved before and after."),
        )))
        # indent=1 / ensure_ascii=False / LF round-trips this file
        # byte-identically, so the diff is the changed fields and nothing else.
        _write_json(UNRESOLVED_PATH, doc)
        return {"before": before, "after": routed}
    raise PartitionError("%r is not in the unresolved manifest" % SONESTA_KEY)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv

    fix = apply_unresolved_manifest_fix() if apply else None
    doc = build_partition()

    if apply:
        _write_json(PARTITION_PATH, doc)

    rec = doc["reconciliation"]
    print("%s -- %s" % (WORK_ORDER, MARKET))
    print("  census ................ %d" % rec["confirmed_identities"])
    print("  published / no-pets ... %d / %d  (resolved %d)"
          % (rec["published_pet_friendly"], rec["verified_no_pets"], rec["resolved"]))
    print("  unresolved ............ %d" % rec["unresolved"])
    print("  reviewed by pass 001 .. %d   never reviewed: %d"
          % (rec["reviewed_in_work_browser_pass_001"],
             rec["never_reviewed_by_any_browser_pass"]))
    shots = doc["evidence_determination"]["screenshot_census"]
    print("  screenshot bytes ...... %s" % (
        shots["image_files"] if shots["scanned"] else "not scanned (absent)"))
    print("  final states:")
    for state, n in doc["final_state_counts"].items():
        if n:
            print("    %-38s %3d" % (state, n))
    audit = doc["collision_audit"]
    print("  collisions: url_reuse=%d code_reuse_in_domain=%d routing_id_reuse=%d"
          % (len(audit["url_reuse"]),
             len(audit["property_code_reuse_within_domain"]),
             len(audit["routing_id_reuse"])))
    drift = doc["authority_agreement"]["unresolved_manifest_vs_identity_routing_url_drift"]
    print("  manifest/routing URL drift: %d" % len(drift))
    for row in drift:
        print("    %s" % row["normalized_name"])
    if fix:
        print("  APPLIED unresolved-manifest fix for %s" % SONESTA_KEY)
        print("    before: %s" % fix["before"])
        print("    after : %s" % fix["after"])
    print("  %s %s" % ("WROTE" if apply else "would write",
                       PARTITION_PATH.relative_to(_REPO_ROOT)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
