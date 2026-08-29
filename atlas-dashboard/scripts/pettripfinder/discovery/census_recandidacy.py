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
        # PTF-DETROIT-ANN-ARBOR-RECANDIDACY-REPAIR-003 (D-002-A). The census
        # contract requires a ZIP, or a city AND a state, before a row may be
        # admitted. This field was absent here, so every committed row that
        # carried a city but no postal code arrived at projection missing half
        # of the only other locality it could have been admitted on, and was
        # held IDENTITY_NO_LOCALITY -- about a property whose committed row
        # names its state plainly.
        "state": row.get("state") or "",
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


#: PTF-DETROIT-ANN-ARBOR-RECANDIDACY-REPAIR-003 (D-002-A). The premises facts a
#: committed census row states about a building. When a live discovery sighting
#: is SILENT on one of these, its silence is not evidence that the committed
#: value is wrong, so the committed value is carried onto the surviving row.
#: When both records state a value and they DISAGREE, nothing is overwritten:
#: the disagreement is surfaced for review, because a rebuild is not entitled to
#: pick a winner between two witnesses on its own.
LOCALITY_FIELDS: Tuple[str, ...] = (
    "address_line", "city", "state", "postal_code", "phone",
    "latitude", "longitude", "website_url",
)

#: Fields where a difference in spelling is not a difference in fact, so a
#: mismatch is only reported when the values differ after normalising.
_CASE_INSENSITIVE = frozenset({"address_line", "city", "state", "website_url"})


def _stated(value) -> bool:
    """A field is STATED when it carries something other than blank."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _same(field: str, a, b) -> bool:
    if field in _CASE_INSENSITIVE:
        return str(a).strip().lower().rstrip("/") == str(b).strip().lower().rstrip("/")
    if field == "phone":
        digits = lambda v: "".join(ch for ch in str(v) if ch.isdigit())[-10:]
        return digits(a) == digits(b)
    return str(a).strip() == str(b).strip()


def _name_tokens(value: str) -> set:
    return {t for t in "".join(
        ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in str(value or "")
    ).split() if t}


def choose_canonical_name(host_name: str, prior_names: Sequence[str]) -> str:
    """Which name the surviving row should carry.

    PTF-DETROIT-ANN-ARBOR-RECANDIDACY-REPAIR-003 (D-002-B). A COMMITTED
    canonical name always outranks a discovery sighting's label. OpenStreetMap
    calls the Best Western Greenfield Inn "Best Western" and misspells the
    Daxton "Daxon Hotel"; neither is authority to rename a reviewed hotel.
    Renaming a committed identity is a FOUNDER RULING about a rebrand, and no
    string comparison can produce one, so this function never promotes the
    discovery name over a committed one.

    When ONE prior row is absorbed, its name wins outright. When SEVERAL are --
    which happens where a building has been rebranded and both the old and new
    identities are committed -- the discovery sighting's own label is the
    evidence of which identity is currently at that address, so the committed
    name sharing the most tokens with it wins. Ties break toward the more
    specific (longer) name, then lexicographically, so the result never depends
    on dict ordering.
    """
    names = [n for n in prior_names if str(n or "").strip()]
    if not names:
        return host_name
    if len(names) == 1:
        return names[0]
    host_tokens = _name_tokens(host_name)
    return sorted(names, key=lambda n: (-len(_name_tokens(n) & host_tokens),
                                        -len(n), n))[0]


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


def _doorway_url(candidate) -> str:
    """The official property page a candidate claims, normalised for comparison."""
    url = str(candidate.get("website_url") or "").strip().lower()
    return url.rstrip("/")


def contested_doorways(prior) -> Dict[str, List[str]]:
    """Street identities where two committed identities are DIFFERENT hotels.

    PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004.

    Street identity answers "is this the same doorway", and a rebuilt census
    leaned on it to answer "is this the same hotel". Those are the same question
    right up until a building is dual-branded, and then they are opposites.
    575 W Big Beaver, Troy holds an EVEN Hotel AND a Hotel Indigo: one address,
    one street number, one ZIP, two hotels, two IHG property codes (dttry and
    dttoy), two official property pages, and a committed census that already
    flags the pair SHARED_ADDRESS. Absorbing either into the other destroys a
    real hotel and reports it as a tidy merge.

    So a doorway is CONTESTED when two or more committed identities there each
    name a DIFFERENT official property page. Two distinct first-party pages is
    the property operators' own statement that these are two properties, and it
    outranks any inference the address could support.

    What this deliberately does NOT catch, and must not: a SUCCESSOR. When a
    Courtyard becomes a Sonesta Select, the stale identity has no official page
    of its own -- there is nothing left to point at -- so only one URL is
    claimed at that doorway and absorption stays available. Distinct evidence
    separates; absent evidence does not.
    """
    urls: Dict[str, Dict[str, str]] = {}
    for candidate in prior:
        key = street_identity(candidate)
        url = _doorway_url(candidate)
        if not key or not url:
            continue
        urls.setdefault(key, {})[url] = str(candidate.get("name") or "")
    return {key: sorted(seen.values())
            for key, seen in urls.items() if len(seen) > 1}


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

    WHAT THE SURVIVING ROW KEEPS FROM THE ROW IT ABSORBED
    ----------------------------------------------------
    PTF-DETROIT-ANN-ARBOR-RECANDIDACY-REPAIR-003. Absorption used to keep the
    fresh row and discard everything the committed row knew except its identity
    key. That is right for a CONTRADICTION and wrong for a SILENCE, and an OSM
    node is silent about almost everything:

    * D-002-A -- Crowne Plaza Auburn Hills is committed with a city, a state and
      a ZIP. It was absorbed into an OSM sighting carrying none of them, the
      merged row kept the sighting's blanks, and projection then held it with
      "the candidate states no city" about a property whose committed row names
      its city plainly. Ten Detroit rows were stranded exactly this way.
    * D-002-B -- the same discard renamed 70 committed identities to whatever
      OSM happened to call the building, including "Daxton Hotel" -> "Daxon
      Hotel" and "Best Western Greenfield Inn" -> "Best Western".

    So a stated committed fact now fills a blank on the survivor, the committed
    canonical name is kept over the sighting's label, and where both records
    state a value and they disagree the survivor is left alone and the conflict
    is recorded on it and in the absorption. Backfilling is not deciding: it
    only ever writes where the live sighting said nothing at all.
    """
    by_street: Dict[str, Dict] = {}
    for candidate in discovery:
        key = street_identity(candidate)
        if key:
            by_street.setdefault(key, candidate)
    # Decided BEFORE any absorption runs, not discovered halfway through it: a
    # doorway is contested for every row at it, and which committed identity
    # happened to be processed first must not decide who survives.
    contested = contested_doorways(prior)
    survivors: List[Dict] = []
    absorptions: List[Dict] = []
    #: host candidate_id -> the committed names it absorbed, in absorption order.
    absorbed_names: Dict[str, List[str]] = {}
    #: host candidate_id -> the host's own observed label, before any rename.
    observed_names: Dict[str, str] = {}

    for candidate in prior:
        key = street_identity(candidate)
        host = by_street.get(key) if key else None
        if host is not None and key in contested:
            # Two committed hotels share this doorway and each names its own
            # official property page. Neither may absorb -- into the discovery
            # sighting or into each other -- so both survive as themselves and
            # the sighting is left unattributed for review. Refusing to merge
            # is the only answer here that cannot destroy a real hotel.
            row = dict(candidate)
            row["same_doorway_distinct_properties"] = list(contested[key])
            row["same_doorway_street_identity"] = key
            survivors.append(row)
            continue
        if host is None:
            survivors.append(dict(candidate))
            continue

        host_id = str(host.get("candidate_id") or "")
        observed_names.setdefault(host_id, str(host.get("name") or ""))

        # -- D-002-A: a silence never overwrites a stated committed fact ----- #
        backfilled: List[str] = []
        conflicts: List[Dict] = []
        for field in LOCALITY_FIELDS:
            mine, theirs = host.get(field), candidate.get(field)
            if not _stated(theirs):
                continue
            if not _stated(mine):
                host[field] = theirs
                backfilled.append(field)
            elif not _same(field, mine, theirs):
                conflicts.append({"field": field,
                                  "discovery_states": mine,
                                  "prior_census_states": theirs})
        if backfilled and host.get("website_url") and not host.get("website_state"):
            host["website_state"] = C.WEBSITE_STATE_OFFICIAL_PRESENT

        # -- D-002-B: the committed canonical name outranks the sighting ----- #
        names = absorbed_names.setdefault(host_id, [])
        prior_name = str(candidate.get("name") or "").strip()
        if prior_name and prior_name not in names:
            names.append(prior_name)
        chosen = choose_canonical_name(observed_names[host_id], names)
        if chosen and chosen != host.get("name"):
            host["name"] = chosen
        host["discovery_observed_name"] = observed_names[host_id]
        if len(names) > 1:
            host["absorbed_committed_names"] = list(names)

        if conflicts:
            existing = list(host.get("recandidacy_conflicts") or ())
            existing.extend(conflicts)
            host["recandidacy_conflicts"] = existing

        absorptions.append({
            "absorbed_candidate_id": candidate.get("candidate_id"),
            "absorbed_name": candidate.get("name"),
            "into_candidate_id": host.get("candidate_id"),
            "into_name": host.get("name"),
            "discovery_observed_name": observed_names[host_id],
            "street_identity": key,
            "basis": "same street identity (number + street words + ZIP); the "
                     "prior census carries no coordinates, so this is the only "
                     "identity both records hold",
            "locality_backfilled_from_prior_census": backfilled,
            "locality_conflicts": conflicts,
        })

        aliases = list(host.get("prior_census_identity_keys") or ())
        prior_key = str(candidate.get("normalized_name") or "")
        if prior_key and prior_key not in aliases:
            aliases.append(prior_key)
        host["prior_census_identity_keys"] = aliases

    # ``into_name`` is written while the loop runs, so where a SECOND committed
    # row later absorbs into the same host and renames it -- a rebranded
    # building whose old and new identities are both committed -- the first
    # record would otherwise still name the host as it was called mid-pass. An
    # absorption record has to say where the row actually LANDED, or a
    # reconciliation that follows it walks to a name that exists nowhere and
    # reports a live identity as lost. Settle every record against the host's
    # final name once the pass is complete.
    final_names = {str(c.get("candidate_id") or ""): str(c.get("name") or "")
                   for c in discovery}
    for record in absorptions:
        landed = final_names.get(str(record.get("into_candidate_id") or ""))
        if landed:
            record["into_name"] = landed
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
           "street_identity", "absorb_prior_by_street", "LOCALITY_FIELDS",
           "contested_doorways",
           "choose_canonical_name"]
