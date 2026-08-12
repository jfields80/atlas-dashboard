"""PTF-DAYTON-RECOVERY-WORKER-002 -- policy observations from fresh captures.

Every record below is built from a raw HTTP capture stored under
``data/worker_runs/pettripfinder/dayton-recovery-002/captures/<slug>.json``
(not committed -- data/ is gitignored). Each quote is asserted to be a
literal substring of that capture's extracted text before the observation
is allowed into the batch, exactly as the earlier Dayton integration did for
the worker's original 44 records.

This module produces validated ``ptf-policy-observation/1.0`` records and
runs them through ``policy_membrane`` + ``readiness`` -- it does NOT write
production authority. Output is the proposed-authority manifest at
``launch_packages/pettripfinder/identity_census/dayton-recovery-002-proposed-authority.json``.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy import policy_membrane as MB   # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO  # noqa: E402
from scripts.pettripfinder.policy import readiness as RD          # noqa: E402
from scripts.pettripfinder import dayton_recovery_002_closeout as CO  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name           # noqa: E402

MARKET = "dayton-oh"
RUN_ID = "dayton-recovery-002"
AS_OF = "2026-08-11"
CAPTURE_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
               / RUN_ID / "captures")
OUT_MANIFEST = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                / "identity_census" / "dayton-recovery-002-proposed-authority.json")
OUT_OBSERVATIONS = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                     / RUN_ID / "observations.json")


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def _resolved_names() -> set:
    """Normalized names this market has since ANSWERED, either way.

    Published pet-friendly and verified-no-pets are both answers; a candidate
    that reached either one is no longer a proposal. Read from the committed
    authority files so this cannot disagree with what actually shipped.
    """
    from scripts.pettripfinder.hotel_exclusions import load_exclusions
    from scripts.pettripfinder.site_data import published_facts_path

    resolved = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                if e.get("market_id") == MARKET}
    facts_path = published_facts_path(MARKET)
    if facts_path.exists():
        doc = json.loads(facts_path.read_text(encoding="utf-8"))
        resolved |= {h["key"] for h in doc.get("hotels", [])}
    return resolved


def _load_capture(slug: str) -> Dict:
    doc = json.loads((CAPTURE_DIR / (slug + ".json")).read_text(encoding="utf-8"))
    doc["_norm_text"] = _norm(doc["text"])
    return doc


def _quote_in_capture(capture: Dict, quote: str) -> bool:
    return _norm(quote) in capture["_norm_text"]


# --------------------------------------------------------------------------- #
# One row per resolved property: (slug, hotel_ref extras, identity_check,
# quotes -> extraction fields, extraction dict, flags).
# --------------------------------------------------------------------------- #

# hotel_ref / identity_check data pulled from the committed census so
# hotel_ref matches the existing identity authority exactly.
CENSUS = {h["slug"]: h for h in json.loads(
    (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
     / "dayton-oh.json").read_text(encoding="utf-8"))["hotels"]}


def _hotel_ref(slug: str) -> Dict:
    row = CENSUS[slug]
    ref = {
        "market_id": MARKET,
        "canonical_name": row["canonical_name"],
        "normalized_name": row["normalized_name"],
    }
    if row.get("street_identity"):
        ref["street_identity"] = row["street_identity"]
    if row.get("_official_url"):
        ref["official_url"] = row["_official_url"]
    if row.get("_property_code"):
        ref["property_code"] = row["_property_code"]
    return ref


def _obs(slug: str, *, obs_n: int, source_url: str, source_type: str,
         name_on_page: str, address_on_page: str = "", phone_on_page: str = "",
         property_code_on_page: str = "", evidence: List[Dict],
         extraction: Dict, flags: List[Dict] = None) -> Dict:
    check = {"name_on_page": name_on_page}
    if address_on_page:
        check["address_on_page"] = address_on_page
    if phone_on_page:
        check["phone_on_page"] = phone_on_page
    if property_code_on_page:
        check["property_code"] = property_code_on_page
    return {
        "obs_id": "%s-%03d" % (slug, obs_n),
        "contract_version": PO.CONTRACT_VERSION,
        "hotel_ref": _hotel_ref(slug),
        "identity_check": check,
        "source_url": source_url,
        "source_type": source_type,
        "authority_tier": PO.SOURCE_TYPE_MAX_TIER[source_type],
        "observed_at": AS_OF,
        "retrieved_at": AS_OF + "T00:00:00Z",
        "capture_method": "deterministic_fetch",
        "evidence": evidence,
        "extraction": extraction,
        "extraction_confidence": "EXACT_QUOTE",
        "flags": flags or [],
    }


def build_batch() -> List[Dict]:
    batch = []

    # -- Americas Best Value Inn & Suites St. Marys (Sonesta) -------------- #
    c = _load_capture("americas-best-value-inn-suites-st-marys")
    q = "Pet Policy: Pets are welcome for a fee of $25 per pet per night."
    assert _quote_in_capture(c, q), "st-marys quote not found"
    batch.append(_obs(
        "americas-best-value-inn-suites-st-marys", obs_n=1,
        source_url=c["url"], source_type="official_structured_data",
        name_on_page="Americas Best Value Inn & Suites St. Marys by Sonesta",
        address_on_page="1321 Celina Road, St. Marys, OH 45885",
        phone_on_page="(419) 394-2341",
        evidence=[{"quote": q, "location": "policies section",
                   "field_refs": ["pets_allowed", "pet_fee", "fee_currency", "fee_basis", "fee_scope"]}],
        extraction={"pets_allowed": "true", "pet_fee": 2500,
                    "fee_currency": "USD", "fee_basis": "per_night",
                    "fee_scope": "per_pet"},
    ))

    # -- Americas Best Value Inn Celina (Sonesta) -- contradictory fee ----- #
    c = _load_capture("americas-best-value-inn-celina")
    q1 = "Small pets are allowed with manager's approval."
    q2 = "Policies Pet policy: Pets are welcome for a fee of $10 per pet per night."
    assert _quote_in_capture(c, q1), "celina quote1 not found"
    assert _quote_in_capture(c, q2), "celina quote2 not found"
    batch.append(_obs(
        "americas-best-value-inn-celina", obs_n=1,
        source_url=c["url"], source_type="official_structured_data",
        name_on_page="Americas Best Value Inn Celina",
        phone_on_page="(419) 586-4656",
        evidence=[
            {"quote": q1, "location": "hotel description blurb",
             "field_refs": ["pets_allowed"]},
            {"quote": q2, "location": "policies section",
             "field_refs": ["pets_allowed"]},
        ],
        # Fee withheld on purpose: the description blurb says "manager's
        # approval, call for fees" while the Policies section states a flat
        # $10/pet/night -- two irreconcilable statements on the SAME page.
        extraction={"pets_allowed": "true"},
        flags=[{"code": "FLAG_MULTI_POLICY_BLOCKS",
                "detail": "the marketing blurb says small pets need manager's "
                          "approval and to call for fees, while the formal "
                          "Policies section states a flat $10/pet/night fee "
                          "-- pet_fee is withheld, not picked"}],
    ))

    # -- Cobblestone Bellefontaine / Indian Lake / Eaton -- $25/dog/night -- #
    cobblestone_priced = [
        ("cobblestone-hotel-suites-bellefontaine",
         "Cobblestone Hotel & Suites Bellefontaine", "171 Dowell Avenue Bellefontaine, OH 43311"),
        ("cobblestone-hotel-suites-indian-lake-russells-point",
         "Cobblestone Hotel & Suites Indian Lake Russells Point", "211 Lincoln Blvd Russells Point, OH 43348"),
        ("cobblestone-hotel-suites-eaton",
         "Cobblestone Hotel & Suites Eaton", "121 E Washington Jackson Road"),
    ]
    q = "Pet Friendly: Dog Friendly: $25/dog per night"
    for slug, name, addr in cobblestone_priced:
        c = _load_capture(slug)
        assert _quote_in_capture(c, q), "%s quote not found" % slug
        batch.append(_obs(
            slug, obs_n=1, source_url=c["url"], source_type="official_property_page",
            name_on_page=name, address_on_page=addr,
            evidence=[{"quote": q, "location": "standard policies block",
                       "field_refs": ["pets_allowed", "species_allowed", "pet_fee", "fee_currency", "fee_basis", "fee_scope"]}],
            extraction={"pets_allowed": "true", "species_allowed": "dogs",
                        "pet_fee": 2500, "fee_currency": "USD",
                        "fee_basis": "per_night", "fee_scope": "per_pet"},
        ))

    # -- Cobblestone Urbana -- dog-friendly, no fee stated ------------------ #
    c = _load_capture("cobblestone-hotel-suites-urbana")
    q = "Pet Friendly: Dog Friendly Cancellation Policy"
    assert _quote_in_capture(c, q), "urbana quote not found"
    batch.append(_obs(
        "cobblestone-hotel-suites-urbana", obs_n=1,
        source_url=c["url"], source_type="official_property_page",
        name_on_page="Cobblestone Hotel & Suites Urbana",
        address_on_page="170 OH-55 Urbana, OH 43078", phone_on_page="937.652.7828",
        evidence=[{"quote": "Pet Friendly: Dog Friendly", "location": "standard policies block",
                   "field_refs": ["pets_allowed", "species_allowed"]}],
        extraction={"pets_allowed": "true", "species_allowed": "dogs"},
    ))

    # -- The Hotel at Dayton South -- bare "Pets Allowed" amenity ---------- #
    c = _load_capture("the-hotel-at-dayton-south")
    q = "Pets Allowed"
    assert _quote_in_capture(c, q), "dayton-south quote not found"
    batch.append(_obs(
        "the-hotel-at-dayton-south", obs_n=1,
        source_url=c["url"], source_type="official_property_page",
        name_on_page="The Hotel at Dayton South",
        phone_on_page="(937) 291-0284",
        evidence=[{"quote": q, "location": "room amenities list",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
    ))

    # -- Hearthstone Inn Cedarville ------------------------------------------ #
    c = _load_capture("hearthstone-inn-cedarville")
    q = "We have some designated pet-friendly rooms also!"
    assert _quote_in_capture(c, q), "hearthstone quote not found"
    batch.append(_obs(
        "hearthstone-inn-cedarville", obs_n=1,
        source_url=c["url"], source_type="official_property_page",
        name_on_page="Hearthstone Inn Cedarville",
        evidence=[{"quote": q, "location": "rooms description",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
    ))

    # -- Extended Stay America x3 -- detailed formal pet policy ------------- #
    esa = [
        ("extended-stay-america-suites-dayton-fairborn",
         "Extended Stay America - Dayton - Fairborn",
         "3131 Presidential Dr., Fairborn, OH 45324", "+1.937.429.0140"),
        ("extended-stay-america-suites-dayton-south",
         "Extended Stay America - Dayton - South",
         "7851 Lois Cir., 45459", "+1.937.439.2022"),
        ("extended-stay-america-suites-dayton---north",
         "Extended Stay America - Dayton - North",
         "6688 Miller Ln., 45414", "+1.937.898.9221"),
    ]
    q_max = "A maximum of two pets are allowed in each suite."
    # PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001. This batch originally split
    # the fee sentence at "for the first six (" and re-joined the halves with
    # an ellipsis, producing an evidence quote that is NOT a substring of the
    # capture while still declaring extraction_confidence EXACT_QUOTE -- and a
    # general_restrictions string that duplicated "six ( six (6)" and
    # paraphrased the approval clause. Each sentence below is contiguous in all
    # three captures and is quoted whole.
    q_fee = ("Pet fees: Not to exceed a $25.00 per day cleaning fee plus tax, "
             "for the first six (6) nights, per pet. Each day thereafter there "
             "is a pet cleaning fee not to exceed a $15.00 per day plus tax, "
             "per pet.")
    q_size = ("Height and length restrictions apply-- pets can be no longer "
              "than 36 inches and no taller than 36 inches.")
    # PTF-DAYTON-CANDIDATE-PROMOTION-001. general_restrictions used to be
    # ``q_fee + " " + q_size``. Both halves are verbatim, but they are NOT
    # adjacent: q_fee comes from the property's fees list and q_size from the
    # Pet Policy narrative, ~9,000 characters apart in every one of the three
    # captures. Joining them produced a value that is not a span of any page --
    # the same "quote that is not a quote" defect the ellipsis fix addressed,
    # just without the ellipsis to make it visible. general_restrictions now
    # carries ONE contiguous sentence. The fee ladder is not published as a
    # fact at all (see the withheld reason in integrate_dayton_recovery_002).
    for slug, name, addr, phone in esa:
        c = _load_capture(slug)
        assert _quote_in_capture(c, q_max), "%s max-pets quote not found" % slug
        assert _quote_in_capture(c, q_fee), "%s fee quote not found" % slug
        assert _quote_in_capture(c, q_size), "%s size quote not found" % slug
        batch.append(_obs(
            slug, obs_n=1, source_url=c["url"], source_type="official_structured_data",
            name_on_page=name, address_on_page=addr, phone_on_page=phone,
            evidence=[
                {"quote": q_max, "location": "Pet Policy section",
                 "field_refs": ["pets_allowed", "pet_count_limit", "pet_count_scope"]},
                {"quote": q_fee,
                 "location": "Pet Policy section (cleaning-fee ladder)",
                 "field_refs": ["general_restrictions"]},
                {"quote": q_size, "location": "Pet Policy section (size limits)",
                 "field_refs": ["general_restrictions"]},
            ],
            # The fee is a tiered non-refundable CLEANING fee (not a nightly
            # rate): $25/day for the first 6 nights, then $15/day/pet
            # thereafter, cap governed by stay length. That shape has no
            # single (basis, amount) pair in this contract's vocabulary, so
            # pet_fee / fee_tiers are withheld rather than collapsed into one
            # number. general_restrictions carries the size limit, which is a
            # single contiguous sentence on the page; the fee ladder is
            # evidence here but is published as no fact.
            extraction={"pets_allowed": "true", "pet_count_limit": 2,
                        "pet_count_scope": "room",
                        "general_restrictions": q_size},
        ))

    # -- Baymont / Wingate Dayton North -- marketing-blurb affirmation ----- #
    wyndham_thin = [
        ("baymont-by-wyndham-dayton-north", "Baymont by Wyndham Dayton North",
         "pets are welcome for an extra nightly fee"),
        ("wingate-by-wyndham-dayton-north", "Wingate by Wyndham Dayton North",
         "you can bring your pet for an extra nightly fee"),
    ]
    for slug, name, q in wyndham_thin:
        c = _load_capture(slug)
        assert _quote_in_capture(c, q), "%s quote not found" % slug
        batch.append(_obs(
            slug, obs_n=1, source_url=c["url"], source_type="official_property_page",
            name_on_page=name,
            # PTF-DAYTON-CANDIDATE-PROMOTION-001: this was labelled "local-area
            # marketing copy", which is where the NEXT section of these pages
            # starts ("What's Next Door" / "Local Hotspots"). The sentence is in
            # the property's own description of its own rooms and services, so
            # the label understated the evidence it describes.
            evidence=[{"quote": q, "location": "property description copy",
                       "field_refs": ["pets_allowed"]}],
            extraction={"pets_allowed": "true"},
            flags=[{"code": "FLAG_MARKETING_ONLY",
                    "detail": "affirms pets are welcome for a fee but states no "
                              "amount; the property's formal {{pets}} policy "
                              "template did not render in the static fetch"}],
        ))

    # -- Hotel Versailles -- JSON-LD negative fact + address correction ---- #
    c = _load_capture("hotel-versailles")
    q = '"petsAllowed": false'
    assert _quote_in_capture(c, q), "hotel-versailles quote not found"
    batch.append(_obs(
        "hotel-versailles", obs_n=1,
        source_url=c["url"], source_type="official_structured_data",
        name_on_page="Hotel Versailles",
        address_on_page="22 North Center Street, Versailles, OH 45380",
        phone_on_page="937.526.3020",
        evidence=[{"quote": q, "location": "JSON-LD LodgingBusiness schema",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "false"},
    ))

    return batch


def main() -> int:
    batch = build_batch()
    validated = PO.validate_emission_batch(batch)
    print("validated %d observations" % len(validated))

    by_hotel: Dict[str, List[Dict]] = {}
    for obs in validated:
        by_hotel.setdefault(obs["hotel_ref"]["normalized_name"], []).append(obs)

    candidates = []
    excluded = []
    for name, obs_list in sorted(by_hotel.items()):
        verdicts = MB.evaluate_batch(obs_list)
        result = RD.derive(obs_list)
        slug = next(s for s, h in CENSUS.items() if h["normalized_name"] == name)
        row = {
            "slug": slug,
            "canonical_name": obs_list[0]["hotel_ref"]["canonical_name"],
            "state": result.state,
            "reasons": list(result.reasons),
            "establishing_fields": sorted(set().union(
                *[PO.establishing_fields(o["extraction"]) for o in obs_list])),
            "observations": [o["obs_id"] for o in obs_list],
            "source_urls": sorted({o["source_url"] for o in obs_list}),
        }
        candidates.append(row)

    # PTF-DAYTON-CANDIDATE-PROMOTION-001. ``candidates`` is this run's proposal
    # and stays as it was written -- it is the record of what the worker put
    # forward. What changes over time is how many of those proposals are still
    # only proposals, so that is DERIVED from committed authority rather than
    # restated: a candidate that has since been published or excluded is
    # resolved and drops out. The release contract's reconciliation cross-check
    # sums this list with ``remaining_unresolved`` to reach the market's
    # unresolved count, so a promotion that forgot to update the contract shows
    # up there as a partition that no longer covers the total.
    resolved = _resolved_names()
    still_proposed = [row for row in candidates
                      if normalize_name(row["canonical_name"]) not in resolved]

    # PTF-DAYTON-WORK-BROWSER-INTEGRATION-001. ``remaining_unresolved`` needs
    # the SAME subtraction, and for the same reason. This run categorised four
    # properties ACCESS_BLOCKED on a static 403 -- three Best Westerns and one
    # Extended Stay America -- while an attended capture of each either already
    # sat on disk or was one first-party GET away. Once a later work order
    # publishes or excludes one of them, leaving it in this list makes the list
    # claim a property is unresolved that authority says is answered, and the
    # release contract's length_sum cross-check double-counts it.
    still_unresolved = [row for row in CO.build_report()
                        if normalize_name(row["canonical_name"]) not in resolved]

    manifest = {
        "_schema": "ptf-dayton-recovery-002-proposed-authority/1.0",
        "market_id": MARKET,
        "generated_at": AS_OF,
        "run_id": RUN_ID,
        "base_authority_commit": "de2e467",
        "candidates_still_proposed": still_proposed,
        "note": ("This module PROPOSES; it never writes publication authority. "
                 "It does not modify hotel_policy_facts_dayton-oh.json, "
                 "seed_businesses.csv or hotel_exclusions.json -- writing those "
                 "is an integration act, performed separately and under review "
                 "by scripts/pettripfinder/integrate_dayton_recovery_002.py. "
                 "PTF-DAYTON-CANDIDATE-PROMOTION-001 has since reviewed the "
                 "fourteen candidates below and adjudicated twelve of them: "
                 "eleven published and one (Hotel Versailles) written to the "
                 "exclusion registry, taking Dayton to 44 published / 7 "
                 "verified-no-pets / 78 unresolved / 129 census. The two that "
                 "remain proposals are listed in candidates_still_proposed. "
                 "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 then took the market "
                 "to 47 / 8 / 74 by publishing three properties and excluding "
                 "one, all four of them read from hash-verified captures and "
                 "all four categorised ACCESS_BLOCKED by this run's static "
                 "fetches; they drop out of remaining_unresolved below, which "
                 "is DERIVED from committed authority for the same reason "
                 "candidates_still_proposed is."),
        "candidates": candidates,
        "remaining_unresolved": still_unresolved,
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
    print("wrote", OUT_MANIFEST)

    OUT_OBSERVATIONS.parent.mkdir(parents=True, exist_ok=True)
    OUT_OBSERVATIONS.write_bytes(json.dumps(validated, indent=2).encode("utf-8"))
    print("wrote", OUT_OBSERVATIONS)

    for row in candidates:
        print(row["slug"], "->", row["state"], row["reasons"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
