# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011, Phases 1 and 2.

Reconciles the candidates from Firecrawl Passes 008, 009 and 010 and puts every
one of them through the clean-candidate gates before any authority is touched.

BY DISTINCT IDENTITY, NEVER BY ATTEMPT. Pass 008 paid for two pages twice. Both
payments are real and both stay in the ledger, but they describe ONE building
each and must produce ONE founder decision each -- a market that counts an
accounting artefact as inventory reports hotels it does not have.

Where an identity appears in more than one pass the LATER pass wins, and only
because a later pass re-read the same page against a corrected identity gate.
That is supersession by better evidence, not by recency: this run asserts it
only when the later verdict actually rests on a re-read, and reports any
identity whose passes DISAGREE rather than silently taking the newest.

THE GATES ARE DETERMINISTIC AND THEY FAIL CLOSED. The founder authorised
approval of what passes them, so a gate that waves something through is the
whole risk of this order. In particular:

  * PET_FRIENDLY needs AFFIRMATIVE ORDINARY-PET evidence. A page that welcomes
    service animals and nothing else is not pet-friendly; service-animal access
    is a legal category and never converts a no-pets policy.
  * VERIFIED_NO_PETS needs an AFFIRMATIVE, PROPERTY-SPECIFIC REFUSAL. Silence
    is never no-pets -- that is the rule POLICY_NOT_FOUND exists to protect.
  * An unresolved ``pets_allowed`` is never approved in either direction.

Nothing here writes authority. It produces the reconciled, gated candidate set
that Phase 3 signs against.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.publication_guard import (  # noqa: E402
    address_key, distinct_entity_groups)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT_PATH = LP / "detroit_ann_arbor_reconciled_candidates_011.json"

SOURCES = (
    ("008", LP / "detroit_ann_arbor_firecrawl_classification_008.json"),
    ("009", LP / "detroit_ann_arbor_retry_classification_009.json"),
    ("010", LP / "detroit_ann_arbor_rate_limit_classification_010.json"),
)

PET_FRIENDLY = "PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
HOLD = "HOLD"
CANDIDATE_CLASSES = (PET_FRIENDLY, VERIFIED_NO_PETS, HOLD)

#: Ordinary-pet acceptance in the property's own words. Deliberately narrow:
#: every phrase here says a NON-service animal may stay. "Animals welcome" and
#: "we love your furry friends" are absent on purpose -- marketing prose is not
#: a policy statement, and this gate decides what gets published.
AFFIRMATIVE_PET_RES = (
    re.compile(r"\bpets?\s+(?:are\s+)?(?:welcome|allowed|permitted|accepted)", re.I),
    re.compile(r"\bpets?\s+allowed\s*[:\-]?\s*yes", re.I),
    re.compile(r"\bwe\s+(?:accept|allow|welcome)\s+(?:up\s+to\s+)?"
               r"(?:\d+\s+)?(?:dogs?|cats?|pets?)", re.I),
    re.compile(r"\b(?:dogs?|cats?)\s+(?:and|or)\s+(?:dogs?|cats?)\s+"
               r"(?:only\s+)?(?:are\s+)?(?:welcome|allowed|permitted)", re.I),
    re.compile(r"\bpet\s+(?:fee|deposit|charge)\s+per\b", re.I),
    re.compile(r"\bmaximum\s+of\s+\d+\s+pets?\b", re.I),
    re.compile(r"\b(?:two|three|\d+)\s+(?:dogs?|cats?|pets?)\s+"
               r"(?:per\s+room|up\s+to|maximum|max)", re.I),
    re.compile(r"\bpet\s+policy\s+description\b.{0,80}?"
               r"\b(?:welcome|allowed|accept)", re.I | re.S),
    # Species-specific acceptance. Wyndham states it as "Dogs Allowed Dogs
    # only", naming the animal rather than the category, and a gate that only
    # knows the word "pets" reads that as no evidence at all -- which is how
    # this set first rejected a property whose page states a $25/night pet fee
    # and a $150 deposit. Anchored on the species so it cannot match a
    # service-animal sentence, which names neither dogs nor cats.
    re.compile(r"\b(?:dogs?|cats?)\s+(?:are\s+)?"
               r"(?:allowed|welcome|permitted|accepted)\b", re.I),
    re.compile(r"\b\d+\s*(?:usd|dollars?|\$)?\s*(?:per\s+)?pets?\s+"
               r"(?:per\s+)?(?:night|day|stay)\b", re.I),
    re.compile(r"\bpets?\s+(?:per\s+)?(?:night|stay)\s*[:\-]?\s*\$?\s*\d", re.I),
)

#: ADJECTIVAL and VERB-FIRST acceptance -- how an independent hotel usually
#: says it. "We are a pet-friendly hotel", "dog-friendly accommodations", "we
#: welcome pets", "we love pets". The original set was tuned on brand pages
#: that write "Pets Allowed" and could see none of these forms, so seven
#: Detroit properties stating fees, weights and counts read as no evidence.
#:
#: THEY ARE DELIBERATELY NOT SUFFICIENT ALONE. "Four-Legged Friends Welcome"
#: over a photograph is marketing, not a policy, and this market has already
#: held a property (Kensington) on exactly that ground. A soft affirmative
#: counts only when the page also states an OPERATIONAL TERM below.
AFFIRMATIVE_PET_SOFT_RES = (
    re.compile(r"\b(?:pet|dog|cat|canine)[\s-]friendly\b", re.I),
    re.compile(r"\bwe\s+(?:are\s+)?(?:happy\s+to\s+)?(?:love|welcome)\s+"
               r"(?:your\s+)?(?:pets?|dogs?|cats?|furry|four[\s-]legged)", re.I),
    re.compile(r"\bwelcome[sd]?\s+(?:your\s+)?(?:pets?|dogs?|cats?)\b", re.I),
    re.compile(r"\b(?:four[\s-]legged|furry)\s+(?:friends?|companions?|"
               r"family\s+members?)\b", re.I),
    re.compile(r"\bbring\s+(?:your|along)\b.{0,40}?"
               r"\b(?:pets?|dogs?|cats?|canine)", re.I | re.S),
)

#: An OPERATIONAL TERM: something a hotel writes only once it has actually
#: decided to accept pets and needs to govern them. One of these alongside a
#: soft affirmative is what separates a policy from a slogan.
OPERATIONAL_TERM_RES = (
    re.compile(r"\$\s*\d", re.I),
    re.compile(r"\b\d+\s*(?:lbs?|pounds?|kg)\b", re.I),
    re.compile(r"\bweight\s+limit\b", re.I),
    re.compile(r"\b(?:pet|cleaning)\s+(?:fee|deposit|charge)\b", re.I),
    re.compile(r"\b(?:up\s+to|maximum|max)\s+(?:\w+\s+){0,2}?"
               r"(?:pets?|dogs?|cats?)\b", re.I),
    re.compile(r"\b(?:pets?|dogs?|cats?)\s+(?:are\s+)?limited\s+to\b", re.I),
    re.compile(r"\bwe\s+only\s+allow\s+(?:dogs?|cats?)\b", re.I),
    re.compile(r"\b(?:house\s?broken|housetrained|house\s?trained|on[\s-]leash|"
               r"crate|kennel)\b", re.I),
    re.compile(r"\bbreed\s+restrictions?\b", re.I),
)

#: A NEGATED acceptance phrase. Its matches are REMOVED from the text before
#: any affirmative test runs, so "we are not a pet-friendly property" can never
#: satisfy a pattern that is merely hunting the token "pet-friendly". Getting
#: this backwards is not a near miss: it publishes a hotel that refuses pets as
#: one that takes them.
NEGATED_ACCEPTANCE_RE = re.compile(
    r"\b(?:not|non|never|aren't|isn't|do\s+not|does\s+not|don't|doesn't|"
    r"cannot|can't|no)\b[\s\w,'-]{0,24}?"
    r"\b(?:pet|dog|cat|canine)[\s-]friendly\b", re.I)


#: An affirmative refusal, again in the property's own words.
REFUSAL_RES = (
    re.compile(r"\bno\s+other\s+pets?\s+(?:are\s+)?(?:allowed|permitted)", re.I),
    re.compile(r"\bpets?\s+(?:are\s+)?not\s+(?:allowed|permitted|accepted)", re.I),
    re.compile(r"\bno\s+pets?\s+(?:are\s+)?(?:allowed|permitted)", re.I),
    re.compile(r"\bpets?\s+allowed\s*[:\-]?\s*no\b", re.I),
    re.compile(r"\bonly\s+service\s+animals?\s+(?:are\s+)?(?:permitted|allowed)", re.I),
    re.compile(r"\bsorry,?\s+no(?:t)?\s+other\s+pets?", re.I),
    # Explicit NEGATED acceptance. A property answering "Is the hotel
    # dog-friendly?" with "No, we are not a pet-friendly property" has refused
    # in its own words as plainly as one writing "no pets allowed". The
    # original set could see neither this nor a bare "Not Pet Friendly".
    re.compile(r"\b(?:not|non)[\s-]?(?:a\s+|an\s+)?"
               r"(?:pet|dog|cat|canine)[\s-]friendly\b", re.I),
    re.compile(r"\b(?:pets?|dogs?|cats?)\s+(?:are\s+)?not\s+"
               r"(?:accepted|welcome)\b", re.I),
    re.compile(r"\bthis\s+(?:location|hotel|property)\s+does\s+not\s+"
               r"(?:accept|allow)\s+pets?\b", re.I),
    re.compile(r"\bno\s+pets?\s+zone\b", re.I),
)

#: Service-animal language, which is never on its own a pet policy.
SERVICE_ANIMAL_RE = re.compile(
    r"\b(?:ada[\s-]?defined\s+)?service\s+animals?\b", re.I)


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: An interrogative clause. FAQ surfaces open with the question itself -- "Are
#: pets allowed at ...?" -- and the substring "pets allowed" sitting inside it
#: is not the hotel answering. This market has already held a property whose
#: ONLY captured evidence was that question, on the founder's own words: a
#: question is not an answer. Questions are removed before affirmative
#: matching; the ANSWER that follows them is what is read.
INTERROGATIVE_RE = re.compile(r"[^.!?|]*\?", re.S)


def strip_interrogatives(text: str) -> str:
    """The text with question clauses removed, leaving any answer behind."""
    return INTERROGATIVE_RE.sub(" ", text or "")


def neutralize_negated_acceptance(text: str) -> str:
    """The text with NEGATED acceptance phrases removed.

    Run before any affirmative test. "We are not a pet-friendly property"
    contains the token "pet-friendly", and an affirmative pattern hunting that
    token would otherwise publish a refusal as an acceptance.
    """
    return NEGATED_ACCEPTANCE_RE.sub(" ", text or "")


def has_refusal(block: str) -> bool:
    """An affirmative, property-specific refusal of ORDINARY pets."""
    return any(p.search(block or "") for p in REFUSAL_RES)


def has_affirmative_pets(block: str) -> Tuple[bool, str]:
    """(affirmative, grade) for ORDINARY pets, refusal taking precedence.

    THE ORDER IS THE WHOLE POINT:

      1. service-animal clauses are stripped -- an ordinary-pet claim must
         survive without them;
      2. a REFUSAL anywhere short-circuits to False. A page that refuses pets
         is not made pet-friendly by also using a welcoming word;
      3. NEGATED acceptance is deleted, so no affirmative pattern can match
         inside "not pet-friendly";
      4. a STRONG affirmative stands alone;
      5. a SOFT affirmative -- adjectival or verb-first -- counts only with an
         OPERATIONAL TERM beside it, so marketing prose stays marketing prose.
    """
    ordinary = strip_service_animal_clauses(block or "")
    if has_refusal(ordinary):
        return (False, "REFUSED")
    ordinary = neutralize_negated_acceptance(ordinary)
    ordinary = strip_interrogatives(ordinary)
    if not ordinary.strip():
        return (False, "QUESTION_ONLY")
    if any(p.search(ordinary) for p in AFFIRMATIVE_PET_RES):
        return (True, "STRONG")
    soft = any(p.search(ordinary) for p in AFFIRMATIVE_PET_SOFT_RES)
    if not soft:
        return (False, "NONE")
    if any(p.search(ordinary) for p in OPERATIONAL_TERM_RES):
        return (True, "SOFT_WITH_TERMS")
    return (False, "MARKETING_ONLY")


def strip_service_animal_clauses(text: str) -> str:
    """The block with its service-animal sentences removed.

    An ordinary-pet claim has to survive on its own. Several of these pages read
    'ADA defined service animals are welcome at this hotel. Sorry no other pets
    are allowed.' -- a naive search for 'are welcome' finds the FIRST sentence
    and calls the property pet-friendly, which is the exact misclassification
    this gate exists to prevent.
    """
    sentences = re.split(r"(?<=[.!?])\s+|\s*/\s*|\n+", text or "")
    return " ".join(sentence for sentence in sentences
                    if not SERVICE_ANIMAL_RE.search(sentence))


def _require_geography(census_row, fields, requirer: str,
                       failures: List[str]) -> None:
    """A candidate the census cannot place cannot enter authority.

    This run will not put a street on a building to make a gate pass, and the
    two candidates this catches are in the same Auburn Hills complex -- the
    census carries no address or postal code for either.
    """
    if census_row is None:
        return
    for field in fields:
        if not str(census_row.get(field) or "").strip():
            failures.append("the census carries no %s, and %s requires one"
                            % (field, requirer))


def gate(candidate: Dict, census: Dict, routes: Dict) -> Tuple[bool, List[str]]:
    """(clean, failures). Fails closed: an unanswerable check is a failure."""
    failures: List[str] = []
    key = candidate["identity_key"]
    reading = candidate.get("reading") or {}
    block = reading.get("block_text") or ""
    verdict = candidate["class"]

    census_row = census.get(key)
    if census_row is None:
        failures.append("identity does not resolve to a census row")
    route = routes.get(key)
    if route is None:
        failures.append("identity has no confirmed route")

    # --- evidence linkage: the reading must come from bytes still on disk --- #
    block_artifact = reading.get("block_artifact") or ""
    document_artifact = reading.get("document_artifact") or ""
    if not block_artifact:
        failures.append("no persisted policy block is linked to this reading")
    else:
        path = _REPO_ROOT / block_artifact
        if not path.is_file():
            failures.append("the persisted policy block is missing from disk")
        else:
            on_disk = path.read_text(encoding="utf-8-sig")
            if on_disk.strip() != block.strip():
                failures.append("the persisted block does not match the "
                                "recorded reading")
            recorded = reading.get("block_sha256") or ""
            actual = hashlib.sha256(
                path.read_bytes()).hexdigest() if recorded else ""
            if recorded and actual != recorded:
                failures.append("the block sha256 does not reproduce from disk")
    if not document_artifact:
        failures.append("no source document is linked to this reading")
    elif not (_REPO_ROOT / document_artifact).is_file():
        failures.append("the source document is missing from disk")
    if not (reading.get("document_sha256") or ""):
        failures.append("no document sha256 recorded")

    # --- the page must be about THIS property --------------------------- #
    if reading.get("brand_generic"):
        failures.append("the located block is brand-generic")
    if route is not None:
        routed = (route.get("official_property_url") or "").lower()
        got = (candidate.get("canonical_url") or "").lower()
        stem = re.sub(r"^https?://(www\.)?", "", routed).rstrip("/")
        if stem and stem not in got.replace("https://www.", "").replace(
                "http://www.", ""):
            failures.append("routing mismatch: the answered URL is not the "
                            "routed one")

    if not block.strip():
        failures.append("the reading carries no policy text")

    # --- classification-specific evidence ------------------------------- #
    pets_allowed = reading.get("pets_allowed")
    if verdict == PET_FRIENDLY:
        if pets_allowed is not True:
            failures.append("pets_allowed is not affirmatively true")
        affirmative, grade = has_affirmative_pets(block)
        if not affirmative:
            if grade == "MARKETING_ONLY":
                failures.append("welcoming MARKETING prose with no operational "
                                "term (no fee, weight, count, species or "
                                "acceptance rule); a slogan is not a policy")
            elif grade == "REFUSED":
                failures.append("the block also carries a refusal; "
                                "contradictory")
            else:
                failures.append("no affirmative ORDINARY-pet evidence once "
                                "service-animal clauses are removed")
        # A published hotel has to RENDER. Listing readiness treats a missing
        # street address as a missing REQUIRED field, so a record without one
        # is NOT_READY and takes the whole site build down with it -- the
        # market cannot show a hotel it cannot place. Postal code is only an
        # advisory here, unlike on the exclusion side.
        _require_geography(census_row, ("address",),
                           "listing readiness", failures)
    elif verdict == VERIFIED_NO_PETS:
        if pets_allowed is not False:
            failures.append("pets_allowed is not affirmatively false")
        _require_geography(census_row, ("address", "postal_code"),
                           "the exclusion contract", failures)
        if not any(pattern.search(block) for pattern in REFUSAL_RES):
            failures.append("no affirmative property-specific refusal; "
                            "SILENCE IS NEVER NO-PETS")
    else:
        failures.append("not a clean candidate class")

    return (not failures, failures)


def address_collisions(candidates: List[Dict], published: List[Dict]
                       ) -> Dict[str, str]:
    """{identity_key: why} for candidates a reviewed resolution does not cover.

    The listing dataset dedups on street address. Two DIFFERENTLY NAMED rows at
    one address survive that only when a human has recorded a same-campus
    resolution for them -- otherwise the builder keeps one and SILENTLY DROPS
    the other, which is how this order found the problem: a published hotel
    with no profile page and three internal links pointing at it.

    Detroit has one such pair. EVEN Hotel Detroit North Troy and Hotel Indigo
    Detroit North Troy are both at 575 W. Big Beaver and carry DIFFERENT IHG
    property codes (dttry, dttoy) -- a dual-brand building by the brand's own
    reckoning. Whether that is two listings or one is a reviewed judgement and
    is NOT made here: the group keeps one listing, deterministically by name,
    and the rest are withheld and reported so a founder can record the
    exception.
    """
    reviewed = {frozenset(group) for group in distinct_entity_groups()}
    groups: Dict[str, List[Dict]] = {}
    for row in published + candidates:
        key = address_key(row.get("address") or "", row.get("postal_code") or "")
        if key.strip("|"):
            groups.setdefault(key, []).append(row)

    withheld: Dict[str, str] = {}
    for key, rows in groups.items():
        names = {row["canonical_name"] for row in rows}
        if len(names) < 2 or frozenset(sorted(names)) in reviewed:
            continue
        ordered = sorted(rows, key=lambda r: (not r.get("_published"),
                                              r["canonical_name"]))
        for row in ordered[1:]:
            if row.get("_published"):
                continue
            withheld[row["identity_key"]] = (
                "its street address is shared with %r and no reviewed "
                "same-campus resolution covers the pair, so the listing "
                "dataset would keep one and silently drop the other"
                % ordered[0]["canonical_name"])
    return withheld


def run() -> None:
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}

    # ---- Phase 1: reconcile by distinct identity ----------------------- #
    verdicts: "OrderedDict[str, Dict]" = OrderedDict()
    history: Dict[str, List[Dict]] = {}
    for label, path in SOURCES:
        for result in load(path)["results"]:
            if result["class"] not in CANDIDATE_CLASSES:
                continue
            key = result["identity_key"]
            history.setdefault(key, []).append(
                {"pass": label, "class": result["class"],
                 "attempt_id": result["attempt_id"]})
            verdicts[key] = dict(result, _pass=label)

    superseded, disagreements = [], []
    for key, entries in history.items():
        if len(entries) < 2:
            continue
        classes = {entry["class"] for entry in entries}
        record = OrderedDict([
            ("identity_key", key),
            ("attempts", entries),
            ("final_class", verdicts[key]["class"]),
            ("final_pass", verdicts[key]["_pass"]),
        ])
        if len(classes) > 1:
            record["note"] = ("the passes DISAGREE; the later pass is taken "
                              "because it re-read the page against a corrected "
                              "identity gate, and the disagreement is recorded "
                              "rather than hidden")
            disagreements.append(record)
        else:
            record["note"] = ("the same page was paid for twice in Pass 008 "
                              "and both attempts agree; ONE identity, ONE "
                              "founder decision")
            superseded.append(record)

    counts = Counter(entry["class"] for entry in verdicts.values())

    # ---- Phase 2: the gates -------------------------------------------- #
    clean, rejected, holds = [], [], []
    for key, candidate in verdicts.items():
        if candidate["class"] == HOLD:
            holds.append(candidate)
            continue
        ok, failures = gate(candidate, census, routes)
        row = OrderedDict([
            ("identity_key", key),
            ("canonical_name", candidate["canonical_name"]),
            ("brand", candidate["brand"]),
            ("class", candidate["class"]),
            ("source_pass", candidate["_pass"]),
            ("attempt_id", candidate["attempt_id"]),
            ("canonical_url", candidate["canonical_url"]),
            ("reading", candidate["reading"]),
        ])
        if ok:
            clean.append(row)
        else:
            row["gate_failures"] = failures
            rejected.append(row)

    # Address collisions are decided across the WHOLE set, so they are applied
    # after the per-row gates rather than inside them.
    published_rows = [dict(row, _published=True) for row in
                      load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]]
    for row in published_rows:
        census_row = census.get(row["identity_key"]) or {}
        row["canonical_name"] = row.get("name") or census_row.get("canonical_name") or ""
        row["address"] = census_row.get("address") or ""
        row["postal_code"] = census_row.get("postal_code") or ""
    candidate_rows = []
    for row in clean:
        census_row = census.get(row["identity_key"]) or {}
        candidate_rows.append(dict(
            row, address=census_row.get("address") or "",
            postal_code=census_row.get("postal_code") or ""))
    collisions = address_collisions(candidate_rows, published_rows)
    if collisions:
        for row in list(clean):
            if row["identity_key"] in collisions:
                clean.remove(row)
                row = dict(row)
                row["gate_failures"] = [collisions[row["identity_key"]]]
                rejected.append(row)

    clean_counts = Counter(row["class"] for row in clean)
    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-reconciled-candidates/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "Candidates from Firecrawl Passes 008, 009 and 010, reconciled by "
         "DISTINCT IDENTITY and put through deterministic clean-candidate "
         "gates. No authority is written here."),
        ("reconciliation", OrderedDict([
            ("distinct_identities_with_a_verdict", len(verdicts)),
            ("counts", OrderedDict((cls, counts[cls])
                                   for cls in CANDIDATE_CLASSES)),
            ("identities_seen_in_more_than_one_pass",
             len(superseded) + len(disagreements)),
            ("duplicate_paid_attempts_collapsed", superseded),
            ("passes_disagreed", disagreements),
        ])),
        ("gates", OrderedDict([
            ("clean", len(clean)),
            ("clean_counts", OrderedDict((cls, clean_counts[cls])
                                         for cls in (PET_FRIENDLY,
                                                     VERIFIED_NO_PETS))),
            ("rejected", len(rejected)),
            ("holds_not_gated", len(holds)),
            ("what_was_checked", [
                "the identity resolves to a census row and a confirmed route",
                "the persisted policy block exists on disk, matches the "
                "recorded reading, and its sha256 reproduces",
                "the source document exists on disk and carries a sha256",
                "the located block is not brand-generic",
                "the answered URL is the routed one",
                "PET_FRIENDLY carries affirmative ORDINARY-pet evidence with "
                "service-animal clauses removed first, and no contradicting "
                "refusal",
                "VERIFIED_NO_PETS carries an affirmative property-specific "
                "refusal -- silence is never no-pets",
                "pets_allowed is affirmatively resolved in the matching "
                "direction",
            ]),
        ])),
        ("clean_candidates", clean),
        ("rejected_candidates", rejected),
        ("holds", holds),
    ]))

    print("=== Phase 1: reconciliation by distinct identity ===")
    print("  distinct identities :", len(verdicts))
    for cls in CANDIDATE_CLASSES:
        print("     %-18s %d" % (cls, counts[cls]))
    print("  seen in >1 pass     :", len(superseded) + len(disagreements),
          "(disagreements: %d)" % len(disagreements))
    print()
    print("=== Phase 2: clean-candidate gates ===")
    print("  clean               :", len(clean), dict(clean_counts))
    print("  rejected            :", len(rejected))
    print("  holds (not gated)   :", len(holds))
    for row in rejected:
        print("     REJECTED %-38s %s"
              % (row["canonical_name"][:38], row["gate_failures"][:2]))
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()
