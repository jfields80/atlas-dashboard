"""PTF-CENSUS-PARTITION-NORMALIZATION-001 -- build every market's authorities.

Derives, from committed evidence only, a canonical census and final partition
for Columbus, Cleveland, Dayton and Cincinnati. Run it twice and it produces
identical bytes; run it after an authority changes and the diff is the change.

    python -m scripts.pettripfinder.build_market_authorities --check
    python -m scripts.pettripfinder.build_market_authorities --write

``--check`` derives everything and reports without touching a file. ``--write``
commits the derived documents to their authority paths. Nothing else is ever
written: no policy fact, no route, no market config.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.census_partition_builder import (
    BuilderError, CENSUS_DIR, PACKAGE_DIR, RECOVERY_CATEGORY_BLOCKERS,
    WORK_BROWSER_OUTCOME_BLOCKERS, WORK_BROWSER_REASON_BLOCKERS, WORK_ORDER,
    census_document, census_row, exclusion_final_state, exclusions_for,
    lodging_state_for_exclusion, load, partition_document, partition_item,
    published_keys, routes_for, seed_rows, slugify, write_json,
)
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
# The LEGACY join key, preserved on every row: several modules -- Cleveland's
# partition generator among them -- still join on it, and an upgrade that
# dropped it would break them silently.
from scripts.pettripfinder.site_data import normalize_name

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
CINCINNATI = "cincinnati-oh"

#: Where each market's partition lives. Cleveland keeps the name its committed
#: 1.0 document already has -- renaming an authority mid-upgrade would make the
#: diff look like a deletion and a creation rather than the upgrade it is.
PARTITION_FILES: Dict[str, str] = {
    COLUMBUS: "columbus_final_partition_001.json",
    CLEVELAND: "cleveland_final_partition_002.json",
    DAYTON: "dayton_final_partition_001.json",
    CINCINNATI: "cincinnati_final_partition_001.json",
}

#: Fixed so the documents are reproducible. The date a derivation ran is not a
#: fact about a hotel, and letting the clock into an authority makes every
#: rebuild a diff.
AS_OF = "2026-08-14"


# ==========================================================================
# Columbus -- the census that never existed
# ==========================================================================

def _routing_locality(route: Mapping) -> Dict[str, str]:
    """City, state and postal for a routing-only identity.

    Routing records carry locality in two places and not always the same one:
    ``identity_context`` for most, and the ``identity_signals_matched`` list
    for five Columbus records that hold only a state there. Both are committed
    evidence recorded by the same review, so both are read -- the alternative
    is a census row with a blank city for a property whose city the authority
    plainly states.
    """
    ctx = route.get("identity_context") or {}
    out = {"address": ctx.get("address", ""), "city": ctx.get("city", ""),
           "state": ctx.get("state", ""),
           "postal_code": (ctx.get("postal_code") or "")[:5],
           "phone": ctx.get("phone", "")}
    for signal in route.get("identity_signals_matched") or ():
        if not isinstance(signal, str) or "=" not in signal:
            continue
        name, _, value = signal.partition("=")
        value = value.strip()
        if name == "city" and not out["city"]:
            out["city"] = value
        elif name == "zip" and not out["postal_code"]:
            out["postal_code"] = value[:5]
        elif name == "street" and not out["address"]:
            out["address"] = value
    return out



def _carried_url(row: Mapping) -> str:
    """The official URL a census row already carries, under either name.

    Dayton and Cincinnati record it as a private ``_official_url``; the 1.1
    row this builder emits promotes it to a real field. Reading both keeps
    the builder idempotent and stops a rebuild silently emptying it.
    """
    return row.get("official_url") or row.get("_official_url") or ""


def _carried_basis(row: Mapping) -> str:
    """The corridor basis a census row already carries, under either name.

    The builder reads the authority it also writes, so it has to be idempotent:
    a 1.0 row spells this ``corridor_basis`` and the 1.1 row this builder emits
    spells it ``assignment_basis``. Reading only the first name silently
    dropped the value on every rebuild, which made the second run of a
    "deterministic" builder differ from the first.

    Phase D owns what these values MEAN. This only carries them across intact.
    """
    return row.get("assignment_basis") or row.get("corridor_basis") or ""


def build_columbus() -> Tuple[Mapping, Mapping, List[str]]:
    """Reconstruct Columbus's 112 identities from committed authority.

    The universe is the union of three committed sets, and they do not overlap:

        89  seed inventory rows this market owns   (88 published + 1 held)
        16  exclusion-registry rows                (14 no-pets + 2 category exit)
         7  routing records for identities in neither

    89 + 16 + 7 = 112, which is the number the audits reported and which had
    until now existed only in a work-order report. Every row below names the
    authority it came from, so the count is auditable rather than asserted.
    """
    notes: List[str] = []
    published = published_keys("hotel_policy_facts.json")
    seed = {ptf_identity_key(r["name"]): r for r in seed_rows(COLUMBUS)}
    exclusions = {ptf_identity_key(e["canonical_name"]): e
                  for e in exclusions_for(COLUMBUS)}
    routes = {ptf_identity_key(r["hotel_ref"]["canonical_name"]): r
              for r in routes_for(COLUMBUS)}

    overlap = set(seed) & set(exclusions)
    if overlap:
        raise BuilderError("Columbus seed and exclusions overlap: %s" % sorted(overlap))
    missing = set(published) - set(seed)
    if missing:
        raise BuilderError("published Columbus records absent from seed: %s"
                           % sorted(missing))

    rows: List[Mapping] = []
    items: List[Mapping] = []

    for key, row in sorted(seed.items()):
        is_published = key in published
        rows.append(census_row(
            identity_key=key, canonical_name=row["name"], slug=slugify(row["name"]),
            market_id=COLUMBUS, address=row.get("address", ""),
            city=row.get("city", ""), state=row.get("state", ""),
            postal_code=(row.get("postal_code") or "")[:5], phone=row.get("phone", ""),
            identity_state=enums.IDENTITY_CONFIRMED,
            lodging_state=enums.LODGING_CONFIRMED,
            policy_state=(enums.POLICY_CONFIRMED if is_published
                          else enums.POLICY_NOT_VERIFIED),
            source=row.get("source_type", ""), source_id=row.get("source_url", ""),
            observed_at=row.get("observed_at", ""),
            carried={"normalized_name": normalize_name(row["name"])},
            provenance="seed_businesses.csv"))
        if is_published:
            items.append(partition_item(
                identity_key=key, canonical_name=row["name"],
                slug=slugify(row["name"]), city=row.get("city", ""),
                state=row.get("state", ""),
                postal_code=(row.get("postal_code") or "")[:5],
                final_state=enums.PUBLISHED_PET_FRIENDLY,
                next_action_source="", determined_by="", updated_at=AS_OF,
                official_url=published[key].get("source_url", "")))
        else:
            # The one held seed row. Its wording is in the seed's pet_policy
            # column and no committed policy record backs it, which is exactly
            # what AWAITING_POLICY_ARTIFACT means -- the words are known, the
            # artifact of the page they were read from is not.
            items.append(partition_item(
                identity_key=key, canonical_name=row["name"],
                slug=slugify(row["name"]), city=row.get("city", ""),
                state=row.get("state", ""),
                postal_code=(row.get("postal_code") or "")[:5],
                final_state=enums.AWAITING_POLICY_ARTIFACT,
                next_action_source="seed_businesses.csv",
                determined_by=WORK_ORDER, updated_at=AS_OF,
                official_url=row.get("website_url", "")))
            notes.append("held seed row -> AWAITING_POLICY_ARTIFACT: %s" % row["name"])

    for key, exc in sorted(exclusions.items()):
        state = exclusion_final_state(exc)
        rows.append(census_row(
            identity_key=key, canonical_name=exc["canonical_name"],
            slug=slugify(exc["canonical_name"]), market_id=COLUMBUS,
            address=exc.get("address", ""), city=exc.get("city", ""),
            state=exc.get("state", ""), postal_code=(exc.get("postal_code") or "")[:5],
            phone=exc.get("phone", ""),
            identity_state=enums.IDENTITY_CONFIRMED,
            lodging_state=lodging_state_for_exclusion(exc),
            policy_state=(enums.VERIFIED_NO_PETS if state == enums.VERIFIED_NO_PETS
                          else enums.POLICY_NOT_VERIFIED),
            source="hotel_exclusions", source_id=exc.get("exclusion_id", ""),
            observed_at=exc.get("observed_at", ""),
            carried={"normalized_name": normalize_name(exc["canonical_name"])},
            provenance="hotel_exclusions.json"))
        items.append(partition_item(
            identity_key=key, canonical_name=exc["canonical_name"],
            slug=slugify(exc["canonical_name"]), city=exc.get("city", ""),
            state=exc.get("state", ""),
            postal_code=(exc.get("postal_code") or "")[:5], final_state=state,
            next_action_source="", determined_by="", updated_at=AS_OF,
            official_url=exc.get("official_url", "")))

    for key, route in sorted(routes.items()):
        if key in seed or key in exclusions:
            continue
        ctx = _routing_locality(route)
        name = route["hotel_ref"]["canonical_name"]
        # A held route cannot back policy work; a confirmed one can, and the
        # obstacle is then simply that nobody has observed a policy on it.
        blocker = (enums.AWAITING_ROUTING_REVIEW
                   if route.get("status") == enums.ROUTING_HELD
                   else enums.AWAITING_POLICY_OBSERVATION)
        rows.append(census_row(
            identity_key=key, canonical_name=name, slug=slugify(name),
            market_id=COLUMBUS, address=ctx.get("address", ""),
            city=ctx.get("city", ""), state=ctx.get("state", ""),
            postal_code=(ctx.get("postal_code") or "")[:5], phone=ctx.get("phone", ""),
            identity_state=enums.IDENTITY_CONFIRMED,
            # Identity and category come from a routing binding rather than a
            # verified lodging record, so the lodging axis says exactly that.
            lodging_state=enums.LODGING_BY_NAME,
            policy_state=enums.POLICY_NOT_VERIFIED,
            source="identity_routing", source_id=route.get("routing_id", ""),
            observed_at=route.get("observed_at", ""),
            carried={"normalized_name": normalize_name(name)},
            provenance="identity_routing.json"))
        items.append(partition_item(
            identity_key=key, canonical_name=name, slug=slugify(name),
            city=ctx.get("city", ""), state=ctx.get("state", ""),
            postal_code=(ctx.get("postal_code") or "")[:5], final_state=blocker,
            next_action_source="identity_routing.json", determined_by=WORK_ORDER,
            updated_at=AS_OF, official_url=route.get("official_property_url", "")))
        notes.append("routing-only identity -> %s: %s" % (blocker, name))

    census = census_document(
        COLUMBUS, rows, captured_at=AS_OF,
        note=("Reconstructed by %s from committed authority only. The universe "
              "is the union of the market's seed inventory, its exclusion "
              "registry and its routing records; the three sets do not "
              "overlap. Every row records the authority it came from."
              % WORK_ORDER),
        source_authorities=["seed_businesses.csv", "hotel_policy_facts.json",
                            "hotel_exclusions.json", "identity_routing.json"])
    partition = partition_document(
        COLUMBUS, items, as_of=AS_OF,
        note=("Disposition of every Columbus identity. Terminal states come "
              "from the committed policy package and exclusion registry; each "
              "unresolved identity carries the single blocker its committed "
              "evidence establishes. No identity is resolved here."),
        source_authorities=["seed_businesses.csv", "hotel_policy_facts.json",
                            "hotel_exclusions.json", "identity_routing.json"])
    return census, partition, notes


# ==========================================================================
# Cleveland -- upgrade in place, membership untouched
# ==========================================================================

def build_cleveland() -> Tuple[Mapping, Mapping, List[str]]:
    """Upgrade Cleveland's 188-identity census and partition to 1.1.

    Membership is not touched. Cleveland's partition is the design the whole
    contract was generalised from; this adds the canonical join key and the
    provenance fields, and nothing else.
    """
    from scripts.pettripfinder.contracts.partition import normalise_blocker

    notes: List[str] = []
    source = load("identity_census/%s.json" % CLEVELAND)
    partition_doc = load("cleveland_final_partition_002.json")

    rows = []
    for h in source["hotels"]:
        key = ptf_identity_key(h["canonical_name"])
        rows.append(census_row(
            identity_key=key, canonical_name=h["canonical_name"],
            display_name=h.get("display_name", ""), slug=h.get("slug", ""),
            market_id=CLEVELAND, address=h.get("address", ""),
            city=h.get("city", ""), state=h.get("state", ""),
            postal_code=(h.get("postal_code") or "")[:5], phone=h.get("phone", ""),
            identity_state=h.get("identity_state", ""),
            lodging_state=h.get("lodging_state", ""),
            policy_state=h.get("policy_state", ""),
            # Phase D owns geography. The existing annotation is carried
            # forward exactly as committed, including its basis.
            corridor=h.get("corridor") or "",
            assignment_basis=_carried_basis(h),
            source=h.get("source", ""), source_id=h.get("source_id", ""),
            observed_at=h.get("observed_at", ""),
            official_url=_carried_url(h),
            carried=h,
            provenance="identity_census/%s.json" % CLEVELAND))

    census = census_document(
        CLEVELAND, rows, captured_at=source.get("captured_at", AS_OF),
        note=("Cleveland's committed 188-identity census, upgraded to 1.1 by "
              "%s. Membership, identity evidence and corridor annotations are "
              "unchanged; the canonical identity key and per-row market "
              "ownership are added." % WORK_ORDER),
        source_authorities=["identity_census/%s.json" % CLEVELAND,
                            "cleveland_final_partition_002.json"],
        carried=source)
    notes.append("partition authored by cleveland_final_partition_002.py "
                 "(not rebuilt here: rebuilding it from the generic template "
                 "would flatten its evidence determination, crosswalk, "
                 "authority-agreement and collision-audit blocks)")
    return census, partition_doc, notes


# ==========================================================================
# Dayton -- axis repair, and a partition that never existed
# ==========================================================================

def _dayton_blocker(work_item: Optional[Mapping],
                    recovery: Optional[Mapping]) -> Tuple[str, str]:
    """The single blocker for one unresolved Dayton identity, and its source.

    PRECEDENCE, and the reason for it: the Work-browser pass is a human
    adjudication that recorded what must happen next, while the recovery pass
    recorded why an automated fetch failed. "hilton.com 403 Forbidden" is a
    fact about our attempt, not about the property, and a partition exists to
    state the next action. So the human ledger wins wherever both describe the
    same identity.
    """
    if work_item is not None:
        reason = work_item.get("reason_code") or ""
        outcome = work_item.get("outcome") or ""
        blocker = (WORK_BROWSER_REASON_BLOCKERS.get(reason)
                   or WORK_BROWSER_OUTCOME_BLOCKERS.get(outcome))
        if blocker:
            return blocker, "dayton_work_browser_pass_001"
    if recovery is not None:
        blocker = RECOVERY_CATEGORY_BLOCKERS.get(recovery.get("category") or "")
        if blocker:
            return blocker, "dayton-recovery-002-proposed-authority"
    raise BuilderError(
        "no committed evidence establishes a blocker (work=%r recovery=%r)"
        % ((work_item or {}).get("outcome"), (recovery or {}).get("category")))


def _dayton_rollups(source: Mapping, rows: Sequence[Mapping]) -> Dict:
    """Dayton's envelope, with its roll-up counts recomputed from the rows.

    The committed document declares ``active_count``/``no_pets_count`` against
    the LODGING axis, which is where the no-pets fact never belonged. Once the
    axis is repaired those two roll-ups describe a shape the rows no longer
    have, and a roll-up that disagrees with the records it summarises is the
    exact failure the manifest doctrine exists to prevent: it looks like
    verification while being stale.

    So they are recomputed. ``no_pets_count`` now counts the POLICY axis, which
    is what it always meant.
    """
    carried = dict(source)
    lodging = Counter(r["lodging_state"] for r in rows)
    policy = Counter(r["policy_state"] for r in rows)
    identity = Counter(r["identity_state"] for r in rows)
    carried["active_count"] = lodging[enums.LODGING_CONFIRMED]
    carried["no_pets_count"] = policy[enums.VERIFIED_NO_PETS]
    carried["count_confirmed"] = identity[enums.IDENTITY_CONFIRMED]
    carried["count_provisional"] = identity[enums.IDENTITY_PROVISIONAL]
    carried["_rollup_note"] = (
        "Recomputed by %s. active_count counts LODGING_CONFIRMED rows and "
        "no_pets_count counts POLICY_STATE VERIFIED_NO_PETS rows: the no-pets "
        "fact moved out of the lodging axis, where it was never a category "
        "statement about the property." % WORK_ORDER)
    return carried



def build_dayton() -> Tuple[Mapping, Mapping, List[str]]:
    notes: List[str] = []
    source = load("identity_census/%s.json" % DAYTON)
    published = published_keys("hotel_policy_facts_%s.json" % DAYTON)
    exclusions = {ptf_identity_key(e["canonical_name"]): e
                  for e in exclusions_for(DAYTON)}
    work = {ptf_identity_key(i["canonical_name"]): i
            for i in load("dayton_work_browser_pass_001.json")["items"]}
    recovery = {ptf_identity_key(r["canonical_name"]): r
                for r in load("identity_census/dayton-recovery-002-proposed-authority.json")
                ["remaining_unresolved"]}

    rows, items = [], []
    for h in source["hotels"]:
        key = ptf_identity_key(h["canonical_name"])
        lodging = h.get("lodging_state", "")
        policy = h.get("policy_state", "")

        # AXIS REPAIR. "LODGING_NO_PETS" puts a policy fact in the category
        # axis: whether a property takes pets has nothing to do with whether it
        # is a hotel. The policy axis on these rows ALREADY carries
        # VERIFIED_NO_PETS, so the repair only restores the lodging value --
        # nothing is inferred, and no new category is invented.
        if lodging in enums.LODGING_AXIS_VIOLATIONS:
            lodging = enums.LODGING_CONFIRMED
            notes.append("lodging axis repaired (LODGING_NO_PETS -> "
                         "LODGING_CONFIRMED): %s" % h["canonical_name"])

        if key in published and policy != enums.POLICY_CONFIRMED:
            if policy == enums.POLICY_NOT_VERIFIED:
                # Stale: the committed policy package is terminal authority and
                # already publishes this property.
                notes.append("stale policy annotation corrected "
                             "(POLICY_NOT_VERIFIED -> POLICY_CONFIRMED): %s"
                             % h["canonical_name"])
                policy = enums.POLICY_CONFIRMED
        if key not in exclusions and policy == enums.VERIFIED_NO_PETS:
            # Claims a captured refusal the exclusion registry does not hold,
            # and the later Work-browser pass recorded the opposite -- the page
            # rendered and stated NO pet policy at all. Withdrawing an
            # unsupported claim, never adding one.
            notes.append("unsupported no-pets annotation withdrawn "
                         "(VERIFIED_NO_PETS -> POLICY_NOT_VERIFIED): %s"
                         % h["canonical_name"])
            policy = enums.POLICY_NOT_VERIFIED

        rows.append(census_row(
            identity_key=key, canonical_name=h["canonical_name"],
            display_name=h.get("display_name", ""), slug=h.get("slug", ""),
            market_id=DAYTON, address=h.get("address", ""), city=h.get("city", ""),
            state=h.get("state", ""), postal_code=(h.get("postal_code") or "")[:5],
            phone=h.get("phone", ""), identity_state=h.get("identity_state", ""),
            lodging_state=lodging, policy_state=policy,
            corridor=h.get("corridor") or "",
            assignment_basis=_carried_basis(h),
            source=h.get("source", ""), source_id=h.get("source_id", ""),
            observed_at=h.get("observed_at", ""),
            official_url=_carried_url(h),
            carried=h,
            provenance="identity_census/%s.json" % DAYTON))

        common = dict(identity_key=key, canonical_name=h["canonical_name"],
                      slug=h.get("slug", ""), city=h.get("city", ""),
                      state=h.get("state", ""),
                      postal_code=(h.get("postal_code") or "")[:5],
                      updated_at=AS_OF)
        if key in published:
            items.append(partition_item(
                final_state=enums.PUBLISHED_PET_FRIENDLY, next_action_source="",
                determined_by="", official_url=published[key].get("source_url", ""),
                **common))
        elif key in exclusions:
            items.append(partition_item(
                final_state=exclusion_final_state(exclusions[key]),
                next_action_source="", determined_by="",
                official_url=exclusions[key].get("official_url", ""), **common))
        else:
            blocker, src = _dayton_blocker(work.get(key), recovery.get(key))
            items.append(partition_item(
                final_state=blocker, next_action_source=src,
                determined_by=WORK_ORDER,
                official_url=_carried_url(h), **common))

    census = census_document(
        DAYTON, rows, captured_at=source.get("captured_at", AS_OF),
        note=("Dayton's committed 129-identity census, upgraded to 1.1 by %s. "
              "Membership unchanged. Eight rows carrying a policy fact in the "
              "lodging axis are repaired, and policy annotations contradicted "
              "by terminal authority are corrected. Corridor annotations are "
              "carried forward untouched for Phase D." % WORK_ORDER),
        source_authorities=["identity_census/%s.json" % DAYTON,
                            "hotel_policy_facts_%s.json" % DAYTON,
                            "hotel_exclusions.json"],
        carried=_dayton_rollups(source, rows))
    partition = partition_document(
        DAYTON, items, as_of=AS_OF,
        note=("Disposition of every Dayton identity. Terminal states come from "
              "the committed policy package and exclusion registry. Unresolved "
              "blockers are taken from the Work-browser adjudication in "
              "preference to the recovery pass's fetch-failure label, because "
              "the partition states what must happen next rather than why an "
              "earlier attempt failed."),
        source_authorities=["identity_census/%s.json" % DAYTON,
                            "hotel_policy_facts_%s.json" % DAYTON,
                            "hotel_exclusions.json",
                            "dayton_work_browser_pass_001.json",
                            "identity_census/dayton-recovery-002-proposed-authority.json"])
    return census, partition, notes


# ==========================================================================
# Cincinnati -- ported, never published
# ==========================================================================

CINCINNATI_SOURCE = "identity_census/cincinnati-oh.json"


def build_cincinnati(source_document: Mapping) -> Tuple[Mapping, Mapping, List[str]]:
    """Port Cincinnati's proposed census into the canonical contract.

    Nothing is published and nothing is resolved. Every identity is unresolved,
    and the blocker each carries is derived from what the census itself records
    about it -- an unresolved identity blocks on identity, a confirmed one with
    no official link blocks on the URL, and one with a link blocks on the
    policy nobody has observed yet.

    The market's geography defects (a corridor basis claimed for rows whose ZIP
    is in no corridor, a tri-state market declared as one state) are preserved
    exactly and reported as Phase D inputs. Fixing them here would hide them.
    """
    notes: List[str] = []
    rows, items = [], []
    for h in source_document["hotels"]:
        key = ptf_identity_key(h["canonical_name"])
        identity_state = h.get("identity_state", "")
        # Read through the same carrier the census emits, or a rebuild
        # sees no links and reclassifies twelve identities.
        has_link = bool(h.get("has_official_link")) or bool(_carried_url(h))

        if identity_state in (enums.IDENTITY_UNRESOLVED, enums.IDENTITY_PROVISIONAL):
            blocker = enums.AWAITING_IDENTITY_RESOLUTION
        elif not has_link:
            blocker = enums.AWAITING_OFFICIAL_URL
        else:
            blocker = enums.AWAITING_POLICY_OBSERVATION

        rows.append(census_row(
            identity_key=key, canonical_name=h["canonical_name"],
            display_name=h.get("display_name", ""), slug=h.get("slug", ""),
            market_id=CINCINNATI, address=h.get("address", ""),
            city=h.get("city", ""), state=h.get("state", ""),
            postal_code=(h.get("postal_code") or "")[:5], phone=h.get("phone", ""),
            identity_state=identity_state,
            lodging_state=h.get("lodging_state", ""),
            policy_state=h.get("policy_state", ""),
            corridor=h.get("corridor") or "",
            assignment_basis=_carried_basis(h),
            source=h.get("source", ""), source_id=h.get("source_id", ""),
            observed_at=h.get("observed_at", ""),
            official_url=_carried_url(h),
            carried=h,
            provenance="worker/ptf-cincinnati-market-001:%s" % CINCINNATI_SOURCE))
        items.append(partition_item(
            identity_key=key, canonical_name=h["canonical_name"],
            slug=h.get("slug", ""), city=h.get("city", ""), state=h.get("state", ""),
            postal_code=(h.get("postal_code") or "")[:5], final_state=blocker,
            next_action_source=CINCINNATI_SOURCE, determined_by=WORK_ORDER,
            updated_at=AS_OF, official_url=_carried_url(h)))

    states = Counter(r["state"] for r in rows)
    notes.append("row states: %s" % dict(states))

    census = census_document(
        CINCINNATI, rows, captured_at=source_document.get("captured_at", AS_OF),
        note=("Cincinnati's proposed market-factory census, ported into the "
              "canonical contract by %s. Nothing is published. The market spans "
              "three states and its committed corridor annotations carry known "
              "defects; both are preserved exactly and belong to Phase D."
              % WORK_ORDER),
        source_authorities=["worker/ptf-cincinnati-market-001:%s" % CINCINNATI_SOURCE],
        carried=source_document)
    partition = partition_document(
        CINCINNATI, items, as_of=AS_OF,
        note=("Every Cincinnati identity is unresolved. No committed evidence "
              "establishes a terminal disposition for any of them, and silence "
              "is not a refusal. Blockers are derived from each identity's own "
              "census state."),
        source_authorities=["worker/ptf-cincinnati-market-001:%s" % CINCINNATI_SOURCE])
    return census, partition, notes


# ==========================================================================
# CLI
# ==========================================================================

def _summary(name: str, census: Mapping, partition: Mapping) -> str:
    counts = partition.get("final_state_counts") or {}
    terminal = sum(counts.get(s, 0) for s in enums.TERMINAL_STATES)
    # Cleveland's partition is authored by its own generator and does not carry
    # a top-level "count"; its items are the count. Reading the document rather
    # than assuming one shape is what lets this summarise both.
    total = partition.get("count")
    if total is None:
        total = len(partition.get("items") or ())
    return ("%-26s census=%3d partition=%3d  published=%3d no-pets=%2d "
            "out-of-cat=%2d unresolved=%3d"
            % (name, census["count"], total,
               counts.get(enums.PUBLISHED_PET_FRIENDLY, 0),
               counts.get(enums.VERIFIED_NO_PETS, 0),
               counts.get(enums.OUT_OF_CURRENT_CATEGORY, 0),
               total - terminal))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="write the derived authorities (default: check only)")
    parser.add_argument("--cincinnati-source", type=Path,
                        help="path to the Cincinnati proposed census to port")
    args = parser.parse_args(argv)

    built: "OrderedDict[str, Tuple[Mapping, Mapping, List[str]]]" = OrderedDict()
    built[COLUMBUS] = build_columbus()
    built[CLEVELAND] = build_cleveland()
    built[DAYTON] = build_dayton()

    cincinnati_path = args.cincinnati_source or (CENSUS_DIR / "cincinnati-oh.json")
    if cincinnati_path.is_file():
        built[CINCINNATI] = build_cincinnati(
            json.loads(cincinnati_path.read_text(encoding="utf-8-sig")))
    else:
        sys.stdout.write("cincinnati source absent (%s); skipping\n" % cincinnati_path)

    out = sys.stdout.write
    out("\n%s\n%s\n" % (WORK_ORDER, "=" * 74))
    for market, (census, partition, notes) in built.items():
        out(_summary(market, census, partition) + "\n")
        for note in notes[:200]:
            out("    %s\n" % note)

    if args.write:
        for market, (census, partition, _notes) in built.items():
            c = write_json(CENSUS_DIR / ("%s.json" % market), census)
            if market == CLEVELAND:
                # Its own generator owns that file.
                out("wrote %s census=%s partition=(its own generator)\n"
                    % (market, c[:12]))
                continue
            p = write_json(PACKAGE_DIR / PARTITION_FILES[market], partition)
            out("wrote %s census=%s partition=%s\n" % (market, c[:12], p[:12]))
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
