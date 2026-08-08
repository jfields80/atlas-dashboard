"""PTF-POLICY-P0-001 -- deterministic Drury policy observation adapter.

Drury was chosen as the first adapter because it is the easy case done
properly: the policy is in the static response, phrased consistently across
properties, and reachable without a browser, a challenge, or a login. That
makes it the right place to prove the observation contract end to end without
the proof resting on anything clever.

LIVE VERIFICATION PERFORMED BEFORE THIS FILE EXISTED (work order §9 gate)
------------------------------------------------------------------------
* Accessible: druryhotels.com property pages return HTTP 200 to a plain
  fetch; the policy is in the static markup, so no rendering and no
  interaction are required.
* Terms: ``druryhotels.com/robots.txt`` disallows ``/location-directory``,
  login, reservation-search and ``*/meetings`` paths. It does NOT disallow
  ``/locations/``, which is where property pages live. Nothing here defeats a
  bot defence, and there is none to defeat.
* Identity bindable: the page prints the property name and street address, so
  the capture-time identity gate can be satisfied from the page itself.
* Quote-backed: the policy is one contiguous sentence group under "Hotel
  Information".

WHAT THIS ADAPTER WILL NOT DO
-----------------------------
It will not infer. Drury states a combined weight limit for two pets; it does
NOT state a per-pet limit, so ``weight_limit_operator`` is emitted as
``combined`` only because the page says "combined", and no per-pet number is
derived from it. It will not populate a field from a sibling property. It will
not decide that "$50 per room" answers "per pet or per room?" for a hotel
whose page says something different.

Pure and deterministic: no network, no clock, no file reads.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy.policy_observation import (  # noqa: E402
    CONTRACT_VERSION,
    PT1_OFFICIAL_PROPERTY,
    validate_observation,
)

BRAND = "drury"
OFFICIAL_DOMAIN = "druryhotels.com"

#: Where on the page the policy sits. Used as ``evidence.location`` so a
#: reviewer can find the sentence again without a screenshot.
POLICY_LOCATION = "Hotel Information section"

#: Sentence-level patterns. Each returns (fields_it_supports, values). A
#: pattern that does not match contributes NOTHING -- there is no fallback and
#: no default, which is the entire point.
_SPECIES_BOTH = re.compile(r"\bdogs?\s+and\s+cats?\s+(?:are\s+)?accepted\b", re.I)
_SPECIES_DOGS_ONLY = re.compile(r"\bdogs?\s+only\b|\bonly\s+dogs?\s+(?:are\s+)?accepted\b", re.I)
#: "$50 per room" / "daily fee of $50 per room"
_FEE = re.compile(
    r"(?:daily\s+fee\s+of\s+)?\$\s*(\d{1,4})(?:\.(\d{2}))?\s*(?:per\s+(room|pet|night))?",
    re.I)
_FEE_DAILY = re.compile(r"\bdaily\s+fee\b|\bper\s+night\b", re.I)
_FEE_PER_ROOM = re.compile(r"\bper\s+room\b", re.I)
_FEE_PER_PET = re.compile(r"\bper\s+pet\b", re.I)
#: "Limit of two pets per room" / "limit of 2 pets"
_COUNT = re.compile(r"\blimit\s+of\s+(\w+)\s+pets?\b", re.I)
_COUNT_PER_ROOM = re.compile(r"\b(?:pets?\s+)?per\s+room\b", re.I)
#: "combined weight of 80 pounds"
_WEIGHT_COMBINED = re.compile(
    r"\bcombined\s+weight\s+of\s+(\d{1,3})\s*(?:pounds|lbs?)\b", re.I)
_WEIGHT_PER_PET = re.compile(
    r"\b(\d{1,3})\s*(?:pounds|lbs?)\s*(?:or\s+less\s*)?per\s+pet\b", re.I)
_SERVICE_ANIMAL = re.compile(r"[^.]*\bservice\s+animals?\b[^.]*\.", re.I)

_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def _int_or_none(token: str) -> Optional[int]:
    token = (token or "").strip().lower()
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token)


def extract_policy_sentences(text: str) -> Tuple[str, ...]:
    """The sentences that actually mention pets. The quote must be what the
    page says, so this returns whole sentences rather than a stitched
    paraphrase."""
    if not text:
        return ()
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return tuple(s.strip() for s in sentences
                 if re.search(r"\bpets?\b|\bdogs?\b|\bcats?\b|\bservice animals?\b", s, re.I))


def extract(text: str) -> Dict:
    """Text -> {extraction, field_refs, quote_fragments, flags}.

    Every populated field is accompanied by the fragment that supports it, so
    the caller can build evidence whose ``field_refs`` are true by construction
    rather than by a later assertion.
    """
    sentences = extract_policy_sentences(text)
    joined = " ".join(sentences)
    extraction: Dict[str, object] = {}
    refs: List[str] = []
    flags: List[Dict[str, str]] = []

    if not joined:
        return {"extraction": {}, "field_refs": [], "quote": "", "flags": []}

    # -- species / acceptance ---------------------------------------------- #
    if _SPECIES_BOTH.search(joined):
        extraction["pets_allowed"] = True
        extraction["species_allowed"] = "dogs_and_cats"
        extraction["cats_allowed"] = True
        refs += ["pets_allowed", "species_allowed", "cats_allowed"]
    elif _SPECIES_DOGS_ONLY.search(joined):
        extraction["pets_allowed"] = True
        extraction["species_allowed"] = "dogs_only"
        # An explicit dogs-only statement IS an explicit negative for cats.
        extraction["cats_allowed"] = False
        refs += ["pets_allowed", "species_allowed", "cats_allowed"]

    # -- fee ---------------------------------------------------------------- #
    fee_match = _FEE.search(joined)
    if fee_match and fee_match.group(1):
        dollars = int(fee_match.group(1))
        cents = int(fee_match.group(2) or 0)
        extraction["pet_fee"] = dollars * 100 + cents      # integer minor units
        extraction["fee_currency"] = "USD"
        refs += ["pet_fee", "fee_currency"]
        if _FEE_DAILY.search(joined):
            extraction["fee_basis"] = "per_night"
            refs.append("fee_basis")
        else:
            extraction["fee_basis"] = "unknown"
            refs.append("fee_basis")
            flags.append({"code": "FLAG_AMBIGUOUS_BASIS",
                          "detail": "the page states an amount without saying "
                                    "whether it is charged per night or per stay"})
        if _FEE_PER_ROOM.search(joined):
            extraction["fee_scope"] = "per_room"
            refs.append("fee_scope")
        elif _FEE_PER_PET.search(joined):
            extraction["fee_scope"] = "per_pet"
            refs.append("fee_scope")
        else:
            extraction["fee_scope"] = "unknown"
            refs.append("fee_scope")
            flags.append({"code": "FLAG_AMBIGUOUS_SCOPE",
                          "detail": "the page states an amount without saying "
                                    "whether it applies per pet or per room"})

    # -- count -------------------------------------------------------------- #
    count_match = _COUNT.search(joined)
    if count_match:
        count = _int_or_none(count_match.group(1))
        if count is not None:
            extraction["pet_count_limit"] = count
            refs.append("pet_count_limit")
            if _COUNT_PER_ROOM.search(joined):
                extraction["pet_count_scope"] = "per_room"
                refs.append("pet_count_scope")

    # -- weight -------------------------------------------------------------- #
    combined = _WEIGHT_COMBINED.search(joined)
    per_pet = _WEIGHT_PER_PET.search(joined)
    if combined:
        extraction["weight_limit"] = int(combined.group(1))
        # "combined" is taken from the page's own word, never inferred from the
        # presence of a two-pet limit.
        extraction["weight_limit_operator"] = "combined"
        refs += ["weight_limit", "weight_limit_operator"]
    elif per_pet:
        extraction["weight_limit"] = int(per_pet.group(1))
        extraction["weight_limit_operator"] = "per_pet"
        refs += ["weight_limit", "weight_limit_operator"]

    # -- service animals: captured verbatim, never read as a pet permission -- #
    service = _SERVICE_ANIMAL.search(joined)
    if service:
        extraction["service_animal_exception"] = service.group(0).strip()
        refs.append("service_animal_exception")
        if "pets_allowed" not in extraction:
            flags.append({"code": "FLAG_SERVICE_ANIMAL_ONLY",
                          "detail": "the page states a service-animal rule and "
                                    "no ordinary pet policy; ADA access is not "
                                    "a pet permission"})

    return {"extraction": extraction, "field_refs": sorted(set(refs)),
            "quote": " ".join(sentences).strip(), "flags": flags}


def observe(*, text: str, hotel_ref: Mapping, source_url: str, obs_id: str,
            observed_at: str, retrieved_at: str, name_on_page: str,
            address_on_page: str = "", snapshot_hash: str = "",
            capture_method: str = "deterministic_fetch") -> Dict:
    """Build one validated ptf-policy-observation/1.0 record from page text.

    The observation is PT1 because a Drury property page is the property's own
    page. That claim is checked downstream by the membrane's booking-mirror
    rule against ``hotel_ref.official_url``, so an adapter pointed at a mirror
    cannot smuggle PT1 through.
    """
    parsed = extract(text)
    evidence = []
    if parsed["quote"]:
        evidence.append({
            "quote": parsed["quote"],
            "location": POLICY_LOCATION,
            "field_refs": parsed["field_refs"],
        })

    identity_check: Dict[str, str] = {"name_on_page": name_on_page}
    if address_on_page:
        identity_check["address_on_page"] = address_on_page

    observation = {
        "obs_id": obs_id,
        "contract_version": CONTRACT_VERSION,
        "hotel_ref": dict(hotel_ref),
        "identity_check": identity_check,
        "source_url": source_url,
        "source_type": "official_property_page",
        "authority_tier": PT1_OFFICIAL_PROPERTY,
        "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "capture_method": capture_method,
        "evidence": evidence,
        "extraction": parsed["extraction"],
        "extraction_confidence": "EXACT_QUOTE",
        "flags": parsed["flags"],
    }
    if snapshot_hash:
        observation["snapshot_hash"] = snapshot_hash
    return validate_observation(observation)


__all__ = ["BRAND", "OFFICIAL_DOMAIN", "POLICY_LOCATION",
           "extract_policy_sentences", "extract", "observe"]
