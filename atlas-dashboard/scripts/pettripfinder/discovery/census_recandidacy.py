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

from typing import Dict, List, Mapping, Optional, Sequence, Tuple

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


NAME_EQUAL = "NAMES_EQUAL"
NAME_PRIOR_ABBREVIATES_FRESH = "PRIOR_NAME_IS_CONTAINED_IN_FRESH_NAME"
NAME_FRESH_ABBREVIATES_PRIOR = "FRESH_NAME_IS_CONTAINED_IN_PRIOR_NAME"
NAME_CONFLICT = "NAMES_SHARE_A_STREET_BUT_NEITHER_CONTAINS_THE_OTHER"


def names_compatible(prior_name: str, fresh_name: str) -> Tuple[bool, str]:
    """May a prior row be absorbed into a fresh row at the same street?

    PTF-INDIANAPOLIS-HARDENED-RECENSUS-002. Street identity alone absorbed 16
    of 56 Indianapolis prior rows into fresh rows with UNRELATED names: two
    dual-brand buildings collapsed to one hotel each (Fairfield Inn and
    SpringHill Suites into the Courtyard at 601 W Washington; Hyatt House into
    Hyatt Place at 130 S Pennsylvania), and a Wingate was absorbed into an
    OpenStreetMap row whose stale name calls that building a Baymont. One
    building, two brands, two pet policies -- and a rebrand is a finding for a
    human, not a merge. So a street match absorbs only when one name contains
    the other or they are equal, the same containment test
    ``census_projection`` applies to coordinate absorption.
    """
    from scripts.pettripfinder.discovery.census_projection import (
        absorption_direction, names_equal_for_absorption)

    if names_equal_for_absorption(prior_name, fresh_name):
        return (True, NAME_EQUAL)
    direction = absorption_direction(prior_name, fresh_name)
    if direction == 1:
        return (True, NAME_PRIOR_ABBREVIATES_FRESH)
    if direction == -1:
        return (True, NAME_FRESH_ABBREVIATES_PRIOR)
    return (False, NAME_CONFLICT)


def absorb_prior_by_street(discovery: Sequence[Mapping],
                           prior: Sequence[Mapping],
                           *, conflicts: Optional[List[Dict]] = None
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
        compatible, relation = names_compatible(
            str(candidate.get("name") or ""), str(host.get("name") or ""))
        if not compatible:
            # Same street, unrelated names: a dual-brand building, a rebrand,
            # or a stale provider name. Both rows survive and both are marked,
            # so the duplicate scan and the founder see them side by side.
            kept = dict(candidate)
            kept["street_shared_with"] = list(kept.get("street_shared_with") or ())
            kept["street_shared_with"].append(str(host.get("candidate_id") or ""))
            shared = list(host.get("street_shared_with") or ())
            shared.append(str(candidate.get("candidate_id") or ""))
            host["street_shared_with"] = shared
            if conflicts is not None:
                conflicts.append({
                    "prior_candidate_id": candidate.get("candidate_id"),
                    "prior_name": candidate.get("name"),
                    "fresh_candidate_id": host.get("candidate_id"),
                    "fresh_name": host.get("name"),
                    "street_identity": key,
                    "relation": relation,
                    "resolution": "NOT_ABSORBED: both rows survive as separate "
                                  "identities at one street for review -- a "
                                  "dual-brand building, a rebrand, or a stale "
                                  "provider name",
                })
            survivors.append(kept)
            continue
        record = {
            "absorbed_candidate_id": candidate.get("candidate_id"),
            "absorbed_name": candidate.get("name"),
            "into_candidate_id": host.get("candidate_id"),
            "into_name": host.get("name"),
            "street_identity": key,
            "name_relation": relation,
            "basis": "same street identity (number + street words + ZIP) and a "
                     "compatible name; the prior census carries no coordinates, "
                     "so the street is the only identity both records hold",
        }
        if relation == NAME_FRESH_ABBREVIATES_PRIOR:
            # The prior build knew this hotel by its fuller name ("Home2 Suites
            # by Hilton Indianapolis Airport"); the provider knows it as a bare
            # brand ("Home2 Suites"). A bare brand is a valid identity key that
            # collides with its siblings -- the third market this has
            # threatened -- so the surviving row takes the fuller name and
            # records where it came from.
            record["name_taken_from_prior"] = candidate.get("name")
            record["fresh_name_replaced"] = host.get("name")
            host["name_before_recandidacy"] = host.get("name")
            host["name"] = candidate.get("name")
            if candidate.get("normalized_name"):
                host["normalized_name"] = candidate.get("normalized_name")
        record["surviving_name"] = host.get("name")
        # A prior row that states its city and state is evidence for a host
        # that states neither: Embassy Suites Indianapolis North was absorbed
        # into an OpenStreetMap row with a street and a ZIP but no city, and
        # the host was then held for NO LOCALITY -- the hotel vanished.
        filled = []
        for field in ("city", "state", "postal_code"):
            if not (host.get(field) or "").strip() and (candidate.get(field) or "").strip():
                host[field] = candidate[field]
                filled.append(field)
        if filled:
            record["locality_taken_from_prior"] = filled
            host["locality_taken_from_prior"] = filled
        absorptions.append(record)
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


def build(*, census: Mapping, discovery: Sequence[Mapping], observed_at: str,
          work_order: str = "") -> Tuple[List[Dict], Dict]:
    """``(merged candidates, absorption document)`` -- the whole recandidacy.

    Louisville (PTF-LOUISVILLE-MARKET-REBUILD-002) drove these three functions by
    hand from a shell; Indianapolis (PTF-INDIANAPOLIS-HARDENED-RECENSUS-002) is
    the second rebuild and the sequence is the same every time, so it is one
    call here and one command below, and the next market needs neither a script
    nor a transcript.
    """
    prior = from_census(census, observed_at=observed_at)
    conflicts: List[Dict] = []
    survivors, absorptions = absorb_prior_by_street(discovery, prior,
                                                    conflicts=conflicts)
    merged = merge(discovery, survivors)
    document = {
        "schema": "ptf-census-recandidacy/1.0",
        "market_id": str(census.get("market_id") or ""),
        "work_order": work_order,
        "prior_census_work_order": str(census.get("work_order") or ""),
        "prior_census_rows": len(prior),
        "fresh_discovery_candidates": len(discovery),
        "absorbed_into_fresh": len(absorptions),
        "prior_rows_surviving_on_their_own_evidence": len(survivors),
        "merged_candidates": len(merged),
        "names_taken_from_prior": sum(1 for a in absorptions
                                      if a.get("name_taken_from_prior")),
        "street_conflicts_not_absorbed": len(conflicts),
        "absorptions": absorptions,
        "street_conflicts": conflicts,
    }
    return merged, document


def main(argv=None) -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Project a committed census back into discovery candidates "
                    "and merge them with fresh discovery, absorbing by street.")
    parser.add_argument("--prior-census", required=True,
                        help="a committed ptf-market-identity-census document; "
                             "read as sightings, never as authority")
    parser.add_argument("--discovery-candidates", action="append", default=[],
                        help="a discovery candidates JSON list; repeatable")
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--work-order", default="")
    parser.add_argument("--out", required=True, help="merged candidates JSON list")
    parser.add_argument("--absorptions-out", default="",
                        help="where to write the absorption document; default "
                             "next to --out as <stem>_prior_absorptions.json")
    args = parser.parse_args(argv)

    census = json.loads(Path(args.prior_census).read_text(encoding="utf-8"))
    discovery: List[Dict] = []
    for path in args.discovery_candidates:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise SystemExit("ERROR: %s is not a candidates list" % path)
        discovery.extend(loaded)
    merged, document = build(census=census, discovery=discovery,
                             observed_at=args.observed_at,
                             work_order=args.work_order)
    document["inputs"] = {
        "prior_census": Path(args.prior_census).as_posix(),
        "discovery_candidates": [Path(p).as_posix() for p in args.discovery_candidates],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    absorptions_out = (Path(args.absorptions_out) if args.absorptions_out
                       else out.with_name(out.stem + "_prior_absorptions.json"))
    absorptions_out.write_text(
        json.dumps(document, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    print("prior census rows        : %d" % document["prior_census_rows"])
    print("fresh discovery          : %d" % document["fresh_discovery_candidates"])
    print("absorbed into fresh      : %d" % document["absorbed_into_fresh"])
    print("prior surviving alone    : %d"
          % document["prior_rows_surviving_on_their_own_evidence"])
    print("merged candidates        : %d" % document["merged_candidates"])
    print("written                  : %s" % out.as_posix())
    print("absorptions              : %s" % absorptions_out.as_posix())
    return 0


__all__ = ["PRIOR_CENSUS_PROVIDER", "CANDIDATE_ID_PREFIX", "candidate_id_for",
           "is_prior_census_candidate", "to_candidate", "from_census", "merge",
           "street_identity", "absorb_prior_by_street", "names_compatible",
           "build", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
