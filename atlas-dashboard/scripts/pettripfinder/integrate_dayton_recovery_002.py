"""PTF-DAYTON-CANDIDATE-PROMOTION-001 -- promote reviewed Dayton candidates.

Turns the fourteen ``dayton-recovery-002`` candidates into committed authority:
inventory rows, per-market policy facts, and one verified-no-pets exclusion.
The captures are not re-run; the stored artifacts under
``data/worker_runs/pettripfinder/dayton-recovery-002/captures/`` are the input,
and every quote below is asserted to be a literal substring of the capture that
carries it before any fact derived from it can publish.

This module APPENDS. ``integrate_dayton_authority`` rebuilds
``hotel_policy_facts_dayton-oh.json`` wholesale from its own table; running it
again would drop these records, so the two are deliberately separate and this
one merges into what is already committed.

WHAT REVIEW CHANGED, AND WHY
----------------------------
The proposal arrived as fourteen POLICY_CONFIRMED candidates. All fourteen
survive as identities -- every capture hash re-derives, every quote is a
literal substring of its own capture's raw HTML (not merely of the worker's
derived ``text`` field), every ``source_url`` equals its capture's URL, and no
candidate page contains a pet refusal anywhere. What did not survive intact is
the set of FACTS proposed on top of them:

  * EXTENDED STAY AMERICA (x3). ``general_restrictions`` was
    ``fee_sentence + " " + size_sentence``. Both halves are verbatim, but they
    are ~9,000 characters apart -- the fee list and the Pet Policy narrative
    are different sections of the page. The join is a value that is a span of
    no page. It now carries the size sentence alone, and the tiered cleaning
    fee publishes as no fact at all: "$25/day for the first six nights, then
    $15/day thereafter, per pet" has no single (basis, amount) pair in this
    schema, and picking one would invent a price.
  * AMERICAS BEST VALUE INN CELINA. The page states a flat $10/pet/night in
    its Policies section and "Please call hotel directly for fees and
    restrictions" in its description. Both are the property's own words and
    they do not reconcile, so no fee publishes. The conditional sentence is
    preserved verbatim instead.
  * SPECIES. "pets" alone is never read as dogs+cats. Only the Cobblestone
    properties, whose pages say "Dog Friendly" in as many words, publish a
    species.
  * WEIGHT. Extended Stay America restricts by DIMENSION (36 inches), not
    weight, and Celina says "small pets". Neither is a weight limit, so
    ``weight_limit`` publishes nowhere in this batch.

TWO CANDIDATES DO NOT PUBLISH AT ALL
------------------------------------
Baymont by Wyndham Dayton North and Wingate by Wyndham Dayton North proposed
``pets_allowed: true`` off a sentence in the property's own description. The
sentence is real and first-party, but ``readiness.derive`` classifies both
POLICY_PARTIAL -- marketing language without a stated policy -- and
POLICY_PARTIAL is not in ``readiness.PUBLISHABLE_STATES``. So fourteen
candidates resolve to eleven published, one excluded, and two still proposed.
The readiness gate is enforced in ``build()``, not just honoured by the table.

HOTEL VERSAILLES
----------------
The one negative finding. Its page carries no visible pet text at all; the
sole evidence is ``"petsAllowed": false`` inside the JSON-LD ``LodgingBusiness``
graph, on the ``@type: Hotel`` node whose ``name``, ``streetAddress`` and
``telephone`` are the property's own -- three first-party identity keys on the
same node as the fact. That is the same evidence shape already accepted for two
Columbus exclusions (Best Western Executive Inn, Best Western Canal Winchester
Inn), so it goes through the existing affirmative-refusal path rather than a
new one, and no prose refusal is invented to satisfy a lexical check.

Run:  python -m scripts.pettripfinder.integrate_dayton_recovery_002 [--apply]
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                    # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD          # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MB              # noqa: E402
from scripts.pettripfinder.site_data import normalize_name                  # noqa: E402

MARKET = "dayton-oh"
CATEGORY = "pet-friendly-hotels"
RUN_ID = "dayton-recovery-002"
AS_OF = "2026-08-11"
REVIEWER = "jfields80"

RUN_DIR = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID
CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "identity_census" / "dayton-oh.json")
FACTS_OUT = (_REPO_ROOT / "launch_packages" / "pettripfinder"
             / "hotel_policy_facts_dayton-oh.json")
PRODUCTION_CSV = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                  / "seed_businesses.csv")

# --------------------------------------------------------------------------- #
# The reviewed table. One entry per promoted identity:
#     field -> (published value, the quote that establishes it)
# A quote that is not found in that property's capture refuses the whole
# record; a field with no quote cannot exist here at all.
# --------------------------------------------------------------------------- #

_Q_ESA_MAX = "A maximum of two pets are allowed in each suite."
_Q_ESA_SIZE = ("Height and length restrictions apply-- pets can be no longer "
               "than 36 inches and no taller than 36 inches.")
_ESA_FEE_WITHHELD = (
    "the page states a tiered non-refundable CLEANING fee -- up to $25/day for "
    "the first six (6) nights per pet, then up to $15/day per pet thereafter -- "
    "which has no single (basis, amount) pair in this schema; publishing either "
    "band alone would misstate the price of any stay of a different length")
_ESA_WEIGHT_WITHHELD = (
    "the property restricts pets by DIMENSION (no longer and no taller than 36 "
    "inches), which is not a weight limit; converting one to the other would "
    "invent a number the page does not state")
_SPECIES_WITHHELD = (
    "the page says \"pets\" and names no species; \"pets\" alone is not dogs+cats")
_COBBLESTONE_Q = "Pet Friendly: Dog Friendly: $25/dog per night"

FACTS: "OrderedDict[str, Dict]" = OrderedDict([

    ("americas-best-value-inn-suites-st-marys", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", "Pet Policy: Pets are welcome for a fee of $25 per pet per night.")),
            ("pet_fee", ("$25.00", "Pet Policy: Pets are welcome for a fee of $25 per pet per night.")),
            ("fee_basis", ("per night", "Pet Policy: Pets are welcome for a fee of $25 per pet per night.")),
            ("fee_scope", ("per pet", "Pet Policy: Pets are welcome for a fee of $25 per pet per night.")),
        ]),
        "withheld": {
            "species_allowed": _SPECIES_WITHHELD,
            "weight_limit": "the page states no size or weight restriction of any kind",
        },
    }),

    ("americas-best-value-inn-celina", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", "Small pets are allowed with manager's approval.")),
            ("general_restrictions", (
                "Small pets are allowed with manager's approval. Please call hotel "
                "directly for fees and restrictions.",
                "Small pets are allowed with manager's approval. Please call hotel "
                "directly for fees and restrictions.")),
        ]),
        "withheld": {
            "pet_fee": (
                "the property states two irreconcilable things on one page: its "
                "description says to call the hotel directly for fees, while its "
                "Policies section states a flat $10 per pet per night. Picking "
                "either one would resolve a contradiction the property has not "
                "resolved"),
            "species_allowed": _SPECIES_WITHHELD,
            "weight_limit": (
                "\"small pets\" is a qualifier, not a measurement; the page states "
                "no pound or dimension limit"),
        },
    }),

    ("cobblestone-hotel-suites-bellefontaine", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _COBBLESTONE_Q)),
            ("species_allowed", ("dogs", _COBBLESTONE_Q)),
            ("pet_fee", ("$25.00", _COBBLESTONE_Q)),
            ("fee_basis", ("per night", _COBBLESTONE_Q)),
            ("fee_scope", ("per pet", _COBBLESTONE_Q)),
        ]),
        "withheld": {"weight_limit": "the page states no weight restriction"},
    }),

    ("cobblestone-hotel-suites-indian-lake-russells-point", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _COBBLESTONE_Q)),
            ("species_allowed", ("dogs", _COBBLESTONE_Q)),
            ("pet_fee", ("$25.00", _COBBLESTONE_Q)),
            ("fee_basis", ("per night", _COBBLESTONE_Q)),
            ("fee_scope", ("per pet", _COBBLESTONE_Q)),
        ]),
        "withheld": {"weight_limit": "the page states no weight restriction"},
    }),

    ("cobblestone-hotel-suites-eaton", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _COBBLESTONE_Q)),
            ("species_allowed", ("dogs", _COBBLESTONE_Q)),
            ("pet_fee", ("$25.00", _COBBLESTONE_Q)),
            ("fee_basis", ("per night", _COBBLESTONE_Q)),
            ("fee_scope", ("per pet", _COBBLESTONE_Q)),
        ]),
        "withheld": {"weight_limit": "the page states no weight restriction"},
    }),

    ("cobblestone-hotel-suites-urbana", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", "Pet Friendly: Dog Friendly")),
            ("species_allowed", ("dogs", "Pet Friendly: Dog Friendly")),
        ]),
        "withheld": {
            # The sibling Cobblestone pages put the rate in this exact slot.
            # This one leaves it empty, which is the property saying nothing --
            # not the property saying "free", and not a licence to carry its
            # siblings' $25 across.
            "pet_fee": (
                "this property's policies block states \"Dog Friendly\" with no "
                "rate following it, where its sibling Cobblestone properties "
                "state \"$25/dog per night\" in the same slot. Silence is not a "
                "price, and a sibling's fee is not this property's fee"),
            "weight_limit": "the page states no weight restriction",
        },
    }),

    ("the-hotel-at-dayton-south", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", "Pets Allowed")),
        ]),
        "withheld": {
            "pet_fee": (
                "the property lists \"Pets Allowed\" as a room amenity and states "
                "no fee, no species and no restriction anywhere on the page"),
            "species_allowed": _SPECIES_WITHHELD,
        },
    }),

    ("hearthstone-inn-cedarville", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", "We have some designated pet-friendly rooms also!")),
        ]),
        "withheld": {
            "pet_fee": "the page affirms pet-friendly rooms exist and states no fee",
            "species_allowed": _SPECIES_WITHHELD,
            "pet_count_limit": (
                "\"some designated pet-friendly rooms\" limits WHICH rooms accept "
                "pets, not how many pets a room accepts"),
        },
    }),

    ("extended-stay-america-suites-dayton-fairborn", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_ESA_MAX)),
            ("pet_count_limit", ("2", _Q_ESA_MAX)),
            ("pet_count_scope", ("room", _Q_ESA_MAX)),
            ("general_restrictions", (_Q_ESA_SIZE, _Q_ESA_SIZE)),
        ]),
        "withheld": {"pet_fee": _ESA_FEE_WITHHELD,
                     "weight_limit": _ESA_WEIGHT_WITHHELD,
                     "species_allowed": _SPECIES_WITHHELD},
    }),

    ("extended-stay-america-suites-dayton-south", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_ESA_MAX)),
            ("pet_count_limit", ("2", _Q_ESA_MAX)),
            ("pet_count_scope", ("room", _Q_ESA_MAX)),
            ("general_restrictions", (_Q_ESA_SIZE, _Q_ESA_SIZE)),
        ]),
        "withheld": {"pet_fee": _ESA_FEE_WITHHELD,
                     "weight_limit": _ESA_WEIGHT_WITHHELD,
                     "species_allowed": _SPECIES_WITHHELD},
    }),

    ("extended-stay-america-suites-dayton---north", {
        "facts": OrderedDict([
            ("pets_allowed", ("true", _Q_ESA_MAX)),
            ("pet_count_limit", ("2", _Q_ESA_MAX)),
            ("pet_count_scope", ("room", _Q_ESA_MAX)),
            ("general_restrictions", (_Q_ESA_SIZE, _Q_ESA_SIZE)),
        ]),
        "withheld": {"pet_fee": _ESA_FEE_WITHHELD,
                     "weight_limit": _ESA_WEIGHT_WITHHELD,
                     "species_allowed": _SPECIES_WITHHELD},
    }),

    # Baymont by Wyndham Dayton North and Wingate by Wyndham Dayton North are
    # deliberately ABSENT. Both carry a genuine first-party affirmation ("pets
    # are welcome for an extra nightly fee" / "you can bring your pet for an
    # extra nightly fee") in the property's own description, and both survive
    # every evidence check in this module. They are still not published:
    # ``readiness.derive`` puts them in POLICY_PARTIAL -- marketing language
    # without a stated policy -- and POLICY_PARTIAL is not in
    # ``readiness.PUBLISHABLE_STATES``. A sentence in a sales blurb affirming
    # that a fee exists, on a page whose formal {{pets}} policy template never
    # rendered, is a lead to re-capture, not an answer. They stay proposed.
    # ``_assert_readiness_gate`` below enforces this rather than trusting the
    # table to stay correct.
])

#: slug -> the affirmative refusal quote on the property's own page.
NO_PETS: Dict[str, str] = {
    "hotel-versailles": '"petsAllowed": false',
}

NO_PETS_NOTE = (
    "Affirmative property-level refusal (structured_pets_allowed_false) read "
    "from the official site's JSON-LD LodgingBusiness graph. The fact sits on "
    "the @type:Hotel node whose name (\"Hotel Versailles\"), streetAddress "
    "(\"22 North Center Street\") and telephone (\"937.526.3020\") are the "
    "property's own -- identity and refusal on the same first-party node. The "
    "page carries no visible pet text at all, so this quote is the whole of the "
    "evidence and no prose refusal is paraphrased into existence. Same evidence "
    "shape as the Columbus Best Western exclusions applied by "
    "PTF-NEGATIVE-EVIDENCE-P0-001. Promoted by PTF-DAYTON-CANDIDATE-PROMOTION-001; "
    "never held a seed row or a policy record."
)


# --------------------------------------------------------------------------- #
# Helpers. Mirrors integrate_dayton_authority so both promotion paths behave
# identically at the file layer.
# --------------------------------------------------------------------------- #

def _write_lf(path: Path, text: str) -> None:
    """LF endings, explicitly -- ``launch_packages/**`` is pinned ``eol=lf``."""
    path.write_bytes(text.encode("utf-8"))


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def _read_json(path: Path) -> Dict:
    return json.loads(path.read_bytes().decode("utf-8"))


def load_census() -> Dict[str, Dict]:
    return {h["slug"]: h for h in _read_json(CENSUS_PATH)["hotels"]}


def load_captures() -> Dict[str, Dict]:
    """Captures indexed by slug, with the hash re-derived from the stored HTML.

    A capture whose ``html_sha256`` does not re-derive is dropped here rather
    than quarantined later: the artifact is the evidence, and one that does not
    match its own hash is not an artifact this module will read a fact from.
    """
    out: Dict[str, Dict] = {}
    caps = RUN_DIR / "captures"
    if not caps.is_dir():
        return out
    for path in sorted(caps.glob("*.json")):
        doc = _read_json(path)
        html = doc.get("html", "")
        declared = doc.get("html_sha256", "")
        if not declared or hashlib.sha256(html.encode("utf-8")).hexdigest() != declared:
            continue
        out[path.stem] = {
            "body": _norm(doc.get("text", "")) + " " + _norm(html),
            "text": _norm(doc.get("text", "")),
            "url": doc.get("url", ""),
            "html_sha256": declared,
        }
    return out


def _policy_block(cap: Dict, quotes: List[str]) -> str:
    """The property's own policy text, whitespace-collapsed.

    Same invariant as ``integrate_dayton_authority._policy_block``: EVERY quote
    published must be inside the returned block, because that is what the
    published record's ``evidence_quote`` and the seed row's ``pet_policy``
    carry, and what ``test_dayton_authority`` checks each fact against.
    """
    body = cap["body"]
    spans = []
    for quote in quotes:
        needle = _norm(quote)
        i = body.find(needle)
        if i >= 0:
            spans.append((i, i + len(needle)))
    if not spans:
        return ""
    start, end = min(s for s, _ in spans), max(e for _, e in spans)
    if end - start <= 900:
        return body[start:end].strip()
    seen, ordered = set(), []
    for i, quote in sorted(zip([s for s, _ in spans], quotes)):
        text = _norm(quote)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return " ".join(ordered)


def readiness_by_slug() -> Dict[str, str]:
    """The readiness state the observation batch derives for each candidate.

    Recomputed from the observations rather than read from the proposed-authority
    manifest: the manifest is the worker's report, and a promotion path must not
    take a publication decision from the thing it is reviewing.
    """
    from scripts.pettripfinder import dayton_recovery_002_observations as OBS
    from scripts.pettripfinder.policy import readiness as RD

    out: Dict[str, str] = {}
    by_slug: Dict[str, List[Dict]] = {}
    for obs in OBS.build_batch():
        by_slug.setdefault(obs["obs_id"].rsplit("-", 1)[0], []).append(obs)
    for slug, obs_list in by_slug.items():
        out[slug] = RD.derive(obs_list).state
    return out


def _assert_readiness_gate(slug: str, states: Dict[str, str]) -> Optional[str]:
    """Refuse any identity whose derived readiness state is not publishable.

    ``readiness.PUBLISHABLE_STATES`` is the repository's own answer to "is this
    enough to publish", and it excludes POLICY_PARTIAL. Without this check the
    reviewed table above is the only thing standing between a marketing blurb
    and a published fact, and a table is exactly the kind of thing that drifts.
    """
    from scripts.pettripfinder.policy import readiness as RD

    state = states.get(slug)
    if state is None:
        return "no observation in the %s batch derives a readiness state" % RUN_ID
    if state not in RD.PUBLISHABLE_STATES:
        return ("readiness state %s is not in PUBLISHABLE_STATES %s"
                % (state, sorted(RD.PUBLISHABLE_STATES)))
    return None


def build(strict: bool = True) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    census = load_census()
    captures = load_captures()
    states = readiness_by_slug()

    accepted: List[Dict] = []
    exclusions: List[Dict] = []
    quarantined: List[Dict] = []

    for slug, spec in FACTS.items():
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        if hotel["identity_state"] != "IDENTITY_CONFIRMED":
            quarantined.append({"slug": slug,
                                "reason": "identity_state is %s, not IDENTITY_CONFIRMED"
                                          % hotel["identity_state"]})
            continue
        cap = captures.get(slug)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no hash-verified capture in %s" % RUN_ID})
            continue
        if cap["url"] != hotel.get("_official_url", ""):
            quarantined.append({"slug": slug,
                                "reason": "capture URL %r is not the census official_url %r"
                                          % (cap["url"], hotel.get("_official_url", ""))})
            continue
        refused = _assert_readiness_gate(slug, states)
        if refused:
            quarantined.append({"slug": slug, "reason": refused})
            continue

        facts: "OrderedDict[str, object]" = OrderedDict()
        evidence: List[Dict] = []
        bad: List[str] = []
        for field, (value, quote) in spec["facts"].items():
            if _norm(quote) not in cap["body"]:
                bad.append("%s: quote is not in the captured page -- %r" % (field, quote))
                continue
            evidence.append(OrderedDict([
                ("field", field), ("quote", quote),
                ("source_url", hotel.get("_official_url", "")),
                ("value", value)]))
            facts[field] = value
        if bad:
            quarantined.append({"slug": slug, "reason": "; ".join(bad)})
            continue

        block = _policy_block(cap, [e["quote"] for e in evidence])
        missing = [e["field"] for e in evidence
                   if _norm(e["quote"]).lower() not in _norm(block).lower()]
        if missing:
            quarantined.append({"slug": slug,
                                "reason": "policy block does not contain the quote for %s"
                                          % ", ".join(missing)})
            continue

        overlap = set(facts) & set(spec.get("withheld", {}))
        if overlap:
            quarantined.append({"slug": slug,
                                "reason": "field(s) both published and withheld: %s"
                                          % ", ".join(sorted(overlap))})
            continue

        accepted.append(OrderedDict([
            ("key", normalize_name(hotel["canonical_name"])),
            ("name", hotel["canonical_name"]),
            ("facts", facts),
            ("evidence", evidence),
            ("evidence_count", len(evidence)),
            ("evidence_quote", block),
            ("source_url", hotel.get("_official_url", "")),
            ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", AS_OF), ("verified_at", AS_OF),
            ("approval", OrderedDict([("approval_date", AS_OF),
                                      ("decision", "APPROVED"),
                                      ("operator", REVIEWER)])),
            ("withheld_fields", OrderedDict(sorted(spec.get("withheld", {}).items()))),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash", cap["html_sha256"]),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
        ]))

    for slug, quote in sorted(NO_PETS.items()):
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        cap = captures.get(slug)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no hash-verified capture for a negative fact"})
            continue
        if _norm(quote) not in cap["body"]:
            quarantined.append({"slug": slug,
                                "reason": "refusal quote is not in the captured page"})
            continue
        rec = OrderedDict([
            ("exclusion_id", "day-%s" % slug),
            ("canonical_name", hotel["canonical_name"]),
            ("normalized_name", normalize_name(hotel["canonical_name"])),
            ("address", hotel.get("address", "")),
            ("city", hotel.get("city", "")), ("state", hotel.get("state", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("official_url", hotel.get("_official_url", "")),
            ("exclusion_state", EX.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", hotel.get("_official_url", "")),
            ("observed_at", AS_OF),
            ("source_hash", cap["html_sha256"]),
            ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
            ("notes", NO_PETS_NOTE), ("market_id", MARKET),
        ])
        rec["record_hash"] = EX.record_hash(rec)
        rec["approval_hash"] = EX.approval_hash(rec)
        exclusions.append(rec)

    if strict and quarantined:
        raise SystemExit("Dayton promotion refused %d record(s):\n%s"
                         % (len(quarantined),
                            "\n".join("  %(slug)s: %(reason)s" % q for q in quarantined)))
    return accepted, exclusions, quarantined


def seed_rows(accepted: List[Dict], census: Dict[str, Dict]) -> List[Dict]:
    by_key = {normalize_name(h["canonical_name"]): h for h in census.values()}
    rows = []
    for rec in accepted:
        hotel = by_key[rec["key"]]
        rows.append({
            "name": hotel["canonical_name"], "category": CATEGORY,
            "address": hotel.get("address", ""), "city": hotel.get("city", ""),
            "state": hotel.get("state", ""),
            "postal_code": hotel.get("postal_code", ""),
            "phone": hotel.get("phone", ""),
            "website_url": hotel.get("_official_url", ""),
            "source_url": hotel.get("_official_url", ""),
            "source_type": "OFFICIAL_PROPERTY", "observed_at": AS_OF,
            "rating": "", "amenities": "",
            # The renderability boundary reads this field: empty means "pending
            # attestation" and the listing is filtered out before the WGE.
            "pet_policy": rec["evidence_quote"],
            "canonical": "", MARKET_ID_FIELD: MARKET,
        })
    return rows


def main() -> int:
    apply = "--apply" in sys.argv
    accepted, exclusions, quarantined = build(strict=False)
    census = load_census()

    states = readiness_by_slug()
    not_promoted = sorted(set(states) - set(FACTS) - set(NO_PETS))

    print("Dayton candidate promotion (%s)" % MARKET)
    print("  promoted pet-friendly : %d" % len(accepted))
    print("  promoted no-pets      : %d" % len(exclusions))
    print("  left proposed         : %d" % len(not_promoted))
    for slug in not_promoted:
        print("      %s: readiness %s" % (slug, states[slug]))
    print("  quarantined           : %d" % len(quarantined))
    for q in quarantined:
        print("      %(slug)s: %(reason)s" % q)
    if quarantined:
        print("\nREFUSING to write: every quote must be in its own capture.")
        return 1

    # The publication guard, on the identities about to publish.
    rows = seed_rows(accepted, census)
    EX.assert_not_excluded_for_publication(
        [(r["name"], r["address"], r["postal_code"]) for r in rows])

    if not apply:
        print("\nDry run. Pass --apply to write.")
        return 0

    doc = _read_json(FACTS_OUT)
    have = {h["key"] for h in doc["hotels"]}
    new = [r for r in accepted if r["key"] not in have]
    doc["hotels"].extend(new)
    _write_lf(FACTS_OUT, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print("\nwrote %s (+%d records, now %d)"
          % (FACTS_OUT.relative_to(_REPO_ROOT), len(new), len(doc["hotels"])))

    exdoc = _read_json(EX.EXCLUSIONS_PATH)
    existing = {r["exclusion_id"] for r in exdoc["exclusions"]}
    added_ex = [r for r in exclusions if r["exclusion_id"] not in existing]
    exdoc["exclusions"].extend(added_ex)
    _write_lf(EX.EXCLUSIONS_PATH, json.dumps(exdoc, indent=2, ensure_ascii=False) + "\n")
    print("wrote %s (+%d)" % (EX.EXCLUSIONS_PATH.relative_to(_REPO_ROOT), len(added_ex)))

    with PRODUCTION_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        current = list(reader)
    have_rows = {(r["name"], r.get(MARKET_ID_FIELD, "")) for r in current}
    added = [r for r in rows if (r["name"], MARKET) not in have_rows]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in current + added:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    _write_lf(PRODUCTION_CSV, buf.getvalue())
    print("wrote %s (+%d rows)" % (PRODUCTION_CSV.relative_to(_REPO_ROOT), len(added)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
