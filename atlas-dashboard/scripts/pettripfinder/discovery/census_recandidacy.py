"""Project a committed identity census back into discovery-candidate rows.

WHY THIS EXISTS
---------------
A market censused before the current engine has a census and no candidates. Its
raw discovery output is gone (``data/`` is gitignored and years of it are not
kept), so the census IS the only surviving record of what discovery found. That
leaves a rebuild with two bad options and one good one:

* Trust the old census as authority. Then a later discovery pass can only ADD,
  never reconcile, and every prior mistake is permanent.
* Throw it away and re-discover. Then real identities that only the old pass
  ever saw are silently lost, and the market's history is discarded because it
  is old rather than because it is wrong.
* Feed it back in AS A CANDIDATE, which is what this does.

``census_projection.project`` then treats prior work and fresh discovery
identically: same absorption, same category veto, same membership test, same
one-disposition-per-candidate ledger. A prior identity that is really a
duplicate of a newly discovered row gets absorbed. One that now falls outside
the corridor registry becomes a boundary decision instead of quietly persisting.
And one that fresh discovery simply never saw survives on its own evidence.

WHAT IT MAY NOT DO
------------------
It carries no verdict across. ``identity_state``, ``lodging_state``,
``policy_state`` and the corridor a prior build assigned are all DROPPED: they
are conclusions of a pipeline this rebuild is re-running, and re-importing a
conclusion as an input is how a census ends up confirming only itself
(PTF-CINCINNATI-RECERTIFICATION-AUDIT-001 found a census built from its own
corridor registry).

What it does carry is OBSERVATION: the name, the coordinates, the address, the
telephone, the official URL, and the provenance of whoever found it. Those are
facts a provider reported, and they are exactly what a candidate is.

Pure and deterministic: no network, no clock.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C

#: Provider label for a row whose only surviving witness is the prior census.
PRIOR_CENSUS_PROVIDER = "PRIOR_CENSUS"

#: Candidate-id prefix, so a re-candidated row is never mistaken for a fresh
#: discovery hit in a ledger, a report, or a duplicate audit.
CANDIDATE_ID_PREFIX = "prior-census"


def candidate_id_for(identity_key: str) -> str:
    return "%s::%s" % (CANDIDATE_ID_PREFIX, identity_key)


def is_prior_census_candidate(candidate: Mapping) -> bool:
    return str(candidate.get("candidate_id") or "").startswith(
        CANDIDATE_ID_PREFIX + "::")


def to_candidate(row: Mapping, *, market_id: str, observed_at: str,
                 source_work_order: str = "") -> Dict:
    """One census row as a discovery candidate.

    ``provider_categories`` is set to ``("hotel",)`` ONLY when the prior build
    recorded a positive lodging confirmation. That is not the prior verdict
    being carried across -- ``classify_category`` still runs and can still veto
    on the name -- it is the statement that a provider once affirmed lodging for
    this row, which is the same thing a fresh candidate's categories say. A row
    the prior build could not confirm arrives with NO categories and is
    classified on its own merits as LODGING_BY_NAME.
    """
    identity = str(row.get("identity_key") or "")
    name = row.get("canonical_name") or row.get("display_name") or ""
    confirmed_lodging = str(row.get("lodging_state") or "") == "LODGING_CONFIRMED"
    record: Dict = {
        "provider": PRIOR_CENSUS_PROVIDER,
        "provider_categories": ["hotel"] if confirmed_lodging else [],
        "phone": row.get("phone") or "",
        "provenance": [
            ["source", "prior committed identity census"],
            ["market_id", market_id],
            ["identity_key", identity],
        ],
    }
    if source_work_order:
        record["provenance"].append(["prior_work_order", source_work_order])
    if row.get("provenance"):
        record["provenance"].append(["prior_provenance", str(row["provenance"])])

    candidate: Dict = {
        "candidate_id": candidate_id_for(identity),
        "market_id": market_id,
        "name": name,
        "normalized_name": row.get("normalized_name") or identity,
        "address_line": row.get("address") or "",
        "city": row.get("city") or "",
        "postal_code": row.get("postal_code") or "",
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "observed_at": observed_at,
        "category_candidates": ["hotel"],
        "source_records": [record],
    }
    url = row.get("official_url") or ""
    if url:
        candidate["website_url"] = url
        candidate["website_state"] = C.WEBSITE_STATE_OFFICIAL_PRESENT
    return candidate


def from_census(census: Mapping, *, observed_at: str) -> List[Dict]:
    """Every row of a committed ``ptf-market-identity-census`` as a candidate."""
    market_id = str(census.get("market_id") or "")
    work_order = str(census.get("work_order") or "")
    return [to_candidate(row, market_id=market_id, observed_at=observed_at,
                         source_work_order=work_order)
            for row in census.get("hotels") or ()]


def street_identity(candidate: Mapping) -> str:
    """The corpus's own address identity for a candidate, or ``""``.

    ``hotel_exclusions.address_key`` is the function the exclusion authority and
    the publication guard already use to decide whether two rows are one
    building: street number + distinctive street words + ZIP. Reusing it here
    means a rebuild reconciles addresses the same way publication does.
    """
    from scripts.pettripfinder.hotel_exclusions import address_key

    key = address_key(candidate.get("address_line") or "",
                      candidate.get("postal_code") or "")
    return key if key.strip("|") else ""


def absorb_prior_by_street(discovery: Sequence[Mapping],
                           prior: Sequence[Mapping]
                           ) -> Tuple[List[Dict], List[Dict]]:
    """``(surviving prior candidates, absorption records)``.

    THE GAP THIS CLOSES. ``census_projection`` absorbs one building seen twice
    by COORDINATE, which is right for two live providers and useless here: a
    census written before the current engine carries no coordinates at all --
    all 130 Louisville rows have ``latitude: null``. Handing prior and fresh
    rows to a coordinate absorber therefore reconciles NOTHING between them, and
    every hotel that both passes saw would enter the census twice under two
    spellings of its name.

    So the prior row is absorbed when it shares a STREET IDENTITY with a fresh
    candidate, which is the one thing both records reliably carry. The fresh row
    survives: it has current coordinates and a live provider behind it, and the
    prior row's own identity key is recorded on it so the census can still be
    traced back to what the earlier build called it.

    Every absorption is returned, never silently applied. The surviving
    discovery candidate is annotated IN PLACE with the prior identity key it
    absorbed -- the first version of this copied the row first, so the alias was
    written to a discarded copy and the trace back to the earlier build's name
    was silently lost. A test asserts the caller's own dict carries it.
    """
    by_street: Dict[str, Dict] = {}
    for candidate in discovery:
        key = street_identity(candidate)
        if key:
            by_street.setdefault(key, candidate)
    survivors: List[Dict] = []
    absorptions: List[Dict] = []
    for candidate in prior:
        key = street_identity(candidate)
        host = by_street.get(key) if key else None
        if host is None:
            survivors.append(dict(candidate))
            continue
        absorptions.append({
            "absorbed_candidate_id": candidate.get("candidate_id"),
            "absorbed_name": candidate.get("name"),
            "into_candidate_id": host.get("candidate_id"),
            "into_name": host.get("name"),
            "street_identity": key,
            "basis": "same street identity (number + street words + ZIP); the "
                     "prior census carries no coordinates, so this is the only "
                     "identity both records hold",
        })
        aliases = list(host.get("prior_census_identity_keys") or ())
        prior_key = str(candidate.get("normalized_name") or "")
        if prior_key and prior_key not in aliases:
            aliases.append(prior_key)
        host["prior_census_identity_keys"] = aliases
    return survivors, absorptions


def merge(discovery: Sequence[Mapping], prior: Sequence[Mapping]) -> List[Dict]:
    """Fresh discovery first, prior-census rows after, ids kept unique.

    Order is deliberate. ``project`` ranks candidates before absorbing, and a
    live provider record outranks a re-candidated one, so a prior row that is
    the same building as a fresh hit is absorbed INTO the fresh hit rather than
    the other way round -- the surviving row is then the one with current
    coordinates and a current provider behind it.
    """
    out: List[Dict] = [dict(c) for c in discovery]
    seen = {str(c.get("candidate_id") or "") for c in out}
    for candidate in prior:
        cid = str(candidate.get("candidate_id") or "")
        if cid in seen:
            continue
        seen.add(cid)
        out.append(dict(candidate))
    return out


__all__ = ["PRIOR_CENSUS_PROVIDER", "CANDIDATE_ID_PREFIX", "candidate_id_for",
           "is_prior_census_candidate", "to_candidate", "from_census", "merge",
           "street_identity", "absorb_prior_by_street"]
