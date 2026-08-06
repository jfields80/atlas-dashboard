"""PTF-EXCLUSIONS -- the tracked authority for identities that must never publish.

Some discovered properties are permanently disqualified by evidence rather than
merely unverified. A hotel whose own official page says "No Pets Allowed" is a
VERIFIED NEGATIVE FACT: re-discovering it every sweep, re-queueing it for
capture, and re-reading the same sentence is wasted work, and publishing it as
pet-friendly would be wrong.

This authority is deliberately SEPARATE from the two publication authorities:

  * ``seed_businesses.csv``      -- display inventory
  * ``hotel_policy_facts.json``  -- published policy records

An exclusion needs no seed row, never enters the policy package, and never
creates a public route. ``site_data.verified_public_hotels`` matches seed rows
to policy records; an identity that is in neither is simply not a hotel the site
knows about, which is exactly the intent. Keeping exclusions out of the policy
package also avoids the production renderer's standing invariant that no
committed record carries ``pets_allowed == "false"``.

THE DISTINCTION THAT MATTERS. A capture that failed is NOT an exclusion:

  HOLD_POLICY_NOT_VERIFIED   we could not read the policy. Temporary. Lives in
                             the review batch, stays eligible for capture, and
                             must never be written here.
  VERIFIED_NO_PETS           the property's own official source states pets are
                             not accepted. Durable, evidence-backed.
  PERMANENTLY_CLOSED /       the identity is gone or is no longer a hotel.
  CONVERTED_TO_NON_HOTEL_USE
  DUPLICATE_IDENTITY /       the identity resolves to another record.
  SUPERSEDED_IDENTITY
  OUTSIDE_MARKET             real hotel, outside the market contract.
  OUT_OF_CURRENT_CATEGORY    real lodging, not in the hotel category today --
                             preserved deliberately so a future category can
                             adopt it rather than rediscover it.
  IDENTITY_INVALID           not a real, separable property.

Nothing here is deleted. An identity reopens only through an explicit reviewed
supersession (``supersession`` block), never by a later sweep silently
re-adding it.

Read-only with respect to every other authority. No network.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

SCHEMA = "ptf-hotel-exclusions/1.0"
EXCLUSIONS_PATH = _REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_exclusions.json"

VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"
CONVERTED_TO_NON_HOTEL_USE = "CONVERTED_TO_NON_HOTEL_USE"
DUPLICATE_IDENTITY = "DUPLICATE_IDENTITY"
SUPERSEDED_IDENTITY = "SUPERSEDED_IDENTITY"
OUTSIDE_MARKET = "OUTSIDE_MARKET"
OUT_OF_CURRENT_CATEGORY = "OUT_OF_CURRENT_CATEGORY"
IDENTITY_INVALID = "IDENTITY_INVALID"

EXCLUSION_STATES = (VERIFIED_NO_PETS, PERMANENTLY_CLOSED, CONVERTED_TO_NON_HOTEL_USE,
                    DUPLICATE_IDENTITY, SUPERSEDED_IDENTITY, OUTSIDE_MARKET,
                    OUT_OF_CURRENT_CATEGORY, IDENTITY_INVALID)

#: States that are a verified statement about the property itself and therefore
#: bar publication outright. The rest bar publication too, but these are the
#: ones a future re-check should treat as "answered", not "unknown".
EVIDENCE_BACKED_STATES = (VERIFIED_NO_PETS, PERMANENTLY_CLOSED,
                          CONVERTED_TO_NON_HOTEL_USE)

#: Never valid in this authority: a failed capture is not an exclusion.
FORBIDDEN_STATES = ("HOLD_POLICY_NOT_VERIFIED", "HOLD_IDENTITY", "HOLD_POLICY_CONFLICT",
                    "HOLD_SCHEMA_GAP", "POLICY_NOT_FOUND", "BLOCKED_403",
                    "BLOCKED_CHALLENGE", "TIMEOUT")

REQUIRED_FIELDS = ("exclusion_id", "canonical_name", "normalized_name", "address",
                   "city", "state", "postal_code", "official_url", "exclusion_state",
                   "evidence_quote", "source_url", "observed_at", "source_hash",
                   "record_hash", "reviewer_id", "reviewed_at", "approval_hash")

#: States whose claim rests on reading a specific sentence on the property's own
#: page. For these the evidence quote may not be empty.
QUOTE_REQUIRED_STATES = (VERIFIED_NO_PETS, PERMANENTLY_CLOSED, CONVERTED_TO_NON_HOTEL_USE)


class ExclusionContractError(ValueError):
    """The exclusion authority is malformed, duplicated or self-contradictory."""


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def address_key(address: str, postal_code: str) -> str:
    """Street number + distinctive street words + ZIP.

    A shared house number is not identity -- 50 W Broad St and 50 N 3rd St are
    different buildings -- so the street words are part of the key.
    """
    a = re.sub(r"[^a-z0-9 ]", " ", (address or "").lower())
    stop = {"n", "s", "e", "w", "north", "south", "east", "west", "st", "street", "rd",
            "road", "dr", "drive", "ave", "avenue", "blvd", "boulevard", "pkwy",
            "parkway", "ln", "lane", "ct", "court", "pl", "place", "ste", "suite"}
    num = re.match(r"\s*(\d+)", address or "")
    words = sorted(t for t in a.split() if t and not t.isdigit() and t not in stop)
    return "%s|%s|%s" % (num.group(1) if num else "", " ".join(words),
                         (postal_code or "").strip()[:5])


def record_hash(record: Dict) -> str:
    return _sha(json.dumps({k: record.get(k) for k in
                            ("canonical_name", "address", "postal_code",
                             "exclusion_state", "evidence_quote", "source_url")},
                           sort_keys=True, ensure_ascii=False))


def approval_hash(record: Dict) -> str:
    return _sha(json.dumps({"record_hash": record.get("record_hash"),
                            "reviewer_id": record.get("reviewer_id"),
                            "reviewed_at": record.get("reviewed_at"),
                            "exclusion_state": record.get("exclusion_state")},
                           sort_keys=True, ensure_ascii=False))


def validate(document: Dict) -> List[Dict]:
    """Fail closed on anything ambiguous. Returns the validated records."""
    if document.get("schema") != SCHEMA:
        raise ExclusionContractError("expected schema %r, got %r" % (SCHEMA, document.get("schema")))
    records = document.get("exclusions")
    if not isinstance(records, list):
        raise ExclusionContractError("'exclusions' must be a list")

    seen_ids, seen_norm, seen_addr = {}, {}, {}
    for r in records:
        missing = [f for f in REQUIRED_FIELDS if not str(r.get(f, "")).strip()]
        if missing:
            raise ExclusionContractError("%s: missing required field(s) %s"
                                         % (r.get("exclusion_id") or r.get("canonical_name"), missing))
        state = r["exclusion_state"]
        if state in FORBIDDEN_STATES:
            raise ExclusionContractError(
                "%s: %r is a temporary hold, not an exclusion. A capture that failed must stay "
                "in the review batch and remain eligible for re-capture."
                % (r["exclusion_id"], state))
        if state not in EXCLUSION_STATES:
            raise ExclusionContractError("%s: unknown exclusion_state %r" % (r["exclusion_id"], state))
        if state in QUOTE_REQUIRED_STATES and not str(r.get("evidence_quote", "")).strip():
            raise ExclusionContractError("%s: %s requires an exact evidence quote"
                                         % (r["exclusion_id"], state))
        if r["normalized_name"] != normalize_name(r["canonical_name"]):
            raise ExclusionContractError("%s: normalized_name does not derive from canonical_name"
                                         % r["exclusion_id"])
        if record_hash(r) != r["record_hash"]:
            raise ExclusionContractError("%s: record_hash does not re-derive" % r["exclusion_id"])
        if approval_hash(r) != r["approval_hash"]:
            raise ExclusionContractError("%s: approval_hash does not re-derive" % r["exclusion_id"])
        if state in (DUPLICATE_IDENTITY, SUPERSEDED_IDENTITY) and not r.get("related_identity"):
            raise ExclusionContractError("%s: %s requires related_identity" % (r["exclusion_id"], state))

        if r["exclusion_id"] in seen_ids:
            raise ExclusionContractError("duplicate exclusion_id %r" % r["exclusion_id"])
        seen_ids[r["exclusion_id"]] = r
        prior = seen_norm.get(r["normalized_name"])
        if prior and prior["exclusion_state"] != state:
            raise ExclusionContractError(
                "conflicting exclusion states for %r: %s vs %s"
                % (r["canonical_name"], prior["exclusion_state"], state))
        if prior:
            raise ExclusionContractError("duplicate excluded identity %r" % r["canonical_name"])
        seen_norm[r["normalized_name"]] = r
        ak = address_key(r["address"], r["postal_code"])
        if ak.strip("|") and ak in seen_addr and seen_addr[ak] != r["normalized_name"]:
            raise ExclusionContractError("two exclusions share one street identity: %r and %r"
                                         % (seen_addr[ak], r["normalized_name"]))
        seen_addr[ak] = r["normalized_name"]
    return records


def load_exclusions(path: Path = None) -> List[Dict]:
    """Validated exclusion records, or [] when the authority is absent."""
    p = Path(path) if path else EXCLUSIONS_PATH
    if not p.exists():
        return []
    return validate(json.loads(p.read_text(encoding="utf-8-sig")))


def _active(records: Iterable[Dict]) -> List[Dict]:
    """Records not reopened by a reviewed supersession."""
    return [r for r in records if not (r.get("supersession") or {}).get("reopened")]


def excluded_names(records: Sequence[Dict] = None, path: Path = None) -> frozenset:
    recs = _active(records if records is not None else load_exclusions(path))
    return frozenset(r["normalized_name"] for r in recs)


def excluded_address_keys(records: Sequence[Dict] = None, path: Path = None) -> frozenset:
    recs = _active(records if records is not None else load_exclusions(path))
    return frozenset(address_key(r["address"], r["postal_code"]) for r in recs
                     if address_key(r["address"], r["postal_code"]).strip("|"))


def exclusion_for(name: str, address: str = "", postal_code: str = "",
                  records: Sequence[Dict] = None, path: Path = None) -> Optional[Dict]:
    """The active exclusion matching this identity by name OR street identity."""
    recs = _active(records if records is not None else load_exclusions(path))
    norm = normalize_name(name or "")
    ak = address_key(address, postal_code)
    for r in recs:
        if r["normalized_name"] == norm:
            return r
        if ak.strip("|") and address_key(r["address"], r["postal_code"]) == ak:
            return r
    return None


def is_excluded(name: str, address: str = "", postal_code: str = "",
                records: Sequence[Dict] = None, path: Path = None) -> bool:
    return exclusion_for(name, address, postal_code, records, path) is not None


def supersede(record: Dict, *, reviewer_id: str, reviewed_at: str, reason: str,
              new_source_url: str, new_evidence_quote: str) -> Dict:
    """Reopen an excluded identity through an explicit reviewed decision.

    The original record and its evidence are preserved; reopening is recorded
    beside them, never by deletion, so the audit trail survives.
    """
    if not (reviewer_id and reviewed_at and reason and new_source_url and new_evidence_quote):
        raise ExclusionContractError(
            "supersession requires reviewer_id, reviewed_at, reason, and NEW official "
            "source evidence -- an identity never reopens implicitly")
    out = dict(record)
    out["supersession"] = {"reopened": True, "reviewer_id": reviewer_id,
                           "reviewed_at": reviewed_at, "reason": reason,
                           "superseding_source_url": new_source_url,
                           "superseding_evidence_quote": new_evidence_quote,
                           "supersedes_record_hash": record.get("record_hash")}
    return out


def assert_not_excluded_for_publication(names_with_addresses: Iterable[Sequence[str]],
                                        records: Sequence[Dict] = None,
                                        path: Path = None) -> None:
    """Promotion gate. Raises if any candidate for publication is excluded."""
    recs = records if records is not None else load_exclusions(path)
    hits = []
    for item in names_with_addresses:
        name = item[0]
        addr = item[1] if len(item) > 1 else ""
        zipc = item[2] if len(item) > 2 else ""
        hit = exclusion_for(name, addr, zipc, recs)
        if hit:
            hits.append((name, hit["exclusion_state"], hit["exclusion_id"]))
    if hits:
        raise ExclusionContractError(
            "refusing to publish excluded identities: %s"
            % "; ".join("%s (%s, %s)" % h for h in sorted(hits)))
