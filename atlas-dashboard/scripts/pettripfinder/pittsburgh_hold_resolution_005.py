# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005 Phases 1-2 -- rebuild the remaining work.

    python -m scripts.pettripfinder.pittsburgh_hold_resolution_005
    python -m scripts.pettripfinder.pittsburgh_hold_resolution_005 --write

REBUILT, NEVER QUOTED FORWARD
------------------------------
Every count here is derived from the committed ledgers and the committed
authority as they stand right now. Nothing is read out of Sync 004's own
application report: PTF-CINCINNATI-FREE-LANE-APPLICATION-007 lost time to an
order's own stale count, and a report is a description of a run, not the state.

The six buckets the order asks for:

  A founder holds            the 9 withheld rows of decisions_003
  B signed but unapplied     signed, and the identity it names holds no
                             authority yet
  C census-add candidates    signed-but-unapplied whose identity the
                             REGISTERED 96 does not contain at all
  D replay candidates        rebuilt separately by the replay module
  E stale/duplicate twins    rows the founder ruled RETIRED_STALE_TWIN or
                             SAFE_MERGE
  F identity-review rows     rows ruled IDENTITY_NOT_CORROBORATED

CLASSIFICATION IS BY PROOF (PHASE 2)
--------------------------------------
Exactly one label per signed-but-unapplied row, and fuzzy name similarity is
never one of them:

  DIRECT_REGISTERED_IDENTITY       the signed key IS a registered key
  REGISTERED_TWIN_BY_OFFICIAL_URL  the bound source URL IS a registered URL
  REGISTERED_TWIN_BY_PROPERTY_CODE same brand-scoped code (marriott:pityu)
  REGISTERED_TWIN_BY_ADDRESS_PHONE same street AND same phone
  TRUE_CENSUS_ADD                  no registered collision on code, URL,
                                   address or phone, AND the first-party
                                   evidence a census row needs is present
  IDENTITY_UNRESOLVED              no collision, but the evidence a census ADD
                                   requires is missing -- so it is a question,
                                   not an add

The last two are the distinction this order exists to draw. Sync 004 lumped
seven rows together as "needs census add"; that was the right refusal but the
wrong resolution, because "no twin" and "provably a new property" are different
claims and only the second may write a census row.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (       # noqa: E402
    CENSUS, MARKET_ID, OBSERVATIONS, PACKAGE, RECENSUS, REPORTS, RULINGS,
    Registry, _load, _write, canonical_url, digits, holds, property_codes,
    signed_decisions, street)

WORK_ORDER = "PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005"
AS_OF = "2026-08-30"
BACKLOG = REPORTS / "pittsburgh_hold_resolution_005_backlog.json"

DIRECT = "DIRECT_REGISTERED_IDENTITY"
TWIN_URL = "REGISTERED_TWIN_BY_OFFICIAL_URL"
TWIN_CODE = "REGISTERED_TWIN_BY_PROPERTY_CODE"
TWIN_ADDR = "REGISTERED_TWIN_BY_ADDRESS_PHONE"
CENSUS_ADD = "TRUE_CENSUS_ADD"
UNRESOLVED = "IDENTITY_UNRESOLVED"


class BacklogError(RuntimeError):
    pass


def _authority() -> Tuple[Dict[str, str], Dict]:
    """``identity_key -> the authority state that answers it``."""
    answered: Dict[str, str] = {}
    for record in _load(PACKAGE)["hotels"]:
        answered[record["identity_key"]] = "PUBLISHED_PET_FRIENDLY"
    shard = MA.load_market_exclusions_document(MARKET_ID)
    for row in shard["exclusions"]:
        answered.setdefault(row["normalized_name"], row["exclusion_state"])
    return answered, shard


def _cross_market_collision(codes, url: str, addr: str, phone: str
                            ) -> Optional[str]:
    """Does any OTHER market already claim this property?

    A census ADD that duplicates another market's identity is the failure the
    global exclusion registry's street-identity guard exists to catch, and it
    is cheaper to catch it before writing than after.
    """
    for market in MA.sharded_market_ids():
        if market == MARKET_ID:
            continue
        for row in MA.load_market_exclusions_document(market)["exclusions"]:
            if url and canonical_url(row.get("official_url")) == url:
                return "%s exclusion %s" % (market, row["normalized_name"])
            if codes & property_codes(row.get("official_url")):
                return "%s exclusion %s" % (market, row["normalized_name"])
        for row in MA.load_market_seed_rows(market):
            if url and canonical_url(row.get("website_url")) == url:
                return "%s seed %s" % (market, row.get("name"))
            if (addr and phone and street(row.get("address")) == addr
                    and digits(row.get("phone")) == phone):
                return "%s seed %s" % (market, row.get("name"))
    return None


def _name_tokens(value: object) -> frozenset:
    return frozenset(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def _bare_registered_stub(row: Mapping, registry: Registry) -> Optional[str]:
    """A registered row this candidate might already be, that cannot collide.

    A census row with no URL, no street and no phone is unfalsifiable by the
    hard signals: it will never collide, so a candidate for the same building
    sails through as a clean ADD. The one thing such a stub does carry is its
    NAME, and when every word of it is already inside the candidate's name at
    the same postal, the two are very likely one hotel.

    Deliberately asymmetric, and that asymmetry is the point. A name is not
    accepted as proof that two rows ARE the same property -- Phase 2 forbids
    it, and this corpus has paid for near-misses at the right postal that were
    different hotels. It is accepted as grounds to REFUSE an add, because the
    cost of being wrong runs one way: a wrong merge is visible and reversible,
    a wrong add publishes two profiles for one building.
    """
    postal = str(row.get("postal_code") or "").strip()
    candidate = _name_tokens(row.get("canonical_name"))
    if not postal or not candidate:
        return None
    for hotel in registry.by_key.values():
        if str(hotel.get("postal_code") or "").strip() != postal:
            continue
        if (canonical_url(hotel.get("official_url")) or street(hotel.get("address"))
                or digits(hotel.get("phone"))):
            continue                      # it can collide; the hard signals rule
        other = _name_tokens(hotel.get("canonical_name"))
        if other and other < candidate:   # strict subset: nothing distinguishes it
            return hotel["identity_key"]
    return None


def classify(signed: Mapping, shadow: Optional[Mapping],
             registry: Registry) -> Dict:
    """Exactly one Phase-2 label, with the evidence that earned it."""
    key = signed["identity_key"]
    target, basis = registry.resolve(signed, shadow)
    if target is not None:
        label = {"DIRECT": DIRECT,
                 "OFFICIAL_URL": TWIN_URL,
                 "PROPERTY_CODE": TWIN_CODE,
                 "ADDRESS+PHONE": TWIN_ADDR}.get(basis)
        if label is None:
            # POSTAL+BRAND+NAME_PREFIX is a NAME argument. The order forbids
            # fuzzy name similarity as identity proof, so it does not qualify
            # as a twin here and falls through to the founder.
            return OrderedDict((("label", UNRESOLVED),
                                ("registered_identity_key", None),
                                ("why", "the only candidate link is a name "
                                        "resemblance at a shared postal (%s), "
                                        "which is not identity proof" % target)))
        return OrderedDict((("label", label),
                            ("registered_identity_key", target),
                            ("why", "matched on %s" % basis)))

    row = shadow or {}
    url = canonical_url(signed.get("bound_source_url") or row.get("official_url"))
    codes = (property_codes(signed.get("bound_source_url"))
             | property_codes(row.get("official_url")))
    addr, phone = street(row.get("address")), digits(row.get("phone"))
    missing = []
    if not addr:
        missing.append("first-party street address")
    if not url:
        missing.append("current official URL")
    if not str(row.get("postal_code") or "").strip():
        missing.append("postal code")
    if not str(row.get("city") or "").strip():
        missing.append("city")
    if not row:
        missing.append("a shadow-recensus row to source the identity from")
    stub = _bare_registered_stub(row, registry)
    if stub is not None:
        return OrderedDict((
            ("label", UNRESOLVED),
            ("registered_identity_key", None),
            ("suspected_registered_twin", stub),
            ("why",
             "the registered census holds %r at the same postal and brand, "
             "carrying NO official URL, street address or phone -- so it "
             "cannot collide on anything, and every word of its name is "
             "already in this candidate's. Absence of comparable fields is "
             "not absence of identity: adding this row could publish a second "
             "profile for one building. A name cannot PROVE identity, but it "
             "is reason enough to refuse a silent ADD." % stub)))
    foreign = _cross_market_collision(codes, url, addr, phone)
    if foreign:
        return OrderedDict((("label", UNRESOLVED),
                            ("registered_identity_key", None),
                            ("why", "another market already claims this "
                                    "property: %s" % foreign)))
    if missing:
        return OrderedDict((("label", UNRESOLVED),
                            ("registered_identity_key", None),
                            ("why", "no registered collision, but a census ADD "
                                    "needs %s" % "; ".join(missing))))
    return OrderedDict((
        ("label", CENSUS_ADD),
        ("registered_identity_key", None),
        ("why", "no registered identity collides on official URL, property "
                "code, street address or phone, and the first-party facts a "
                "census row requires are all present"),
        ("property_codes", sorted(codes)),
        ("address", row.get("address")),
        ("phone", row.get("phone")),
        ("postal_code", row.get("postal_code")),
        ("city", row.get("city")),
        ("official_url", url),
    ))


def build() -> Dict:
    census = _load(CENSUS)["hotels"]
    if len(census) != 96:
        raise BacklogError("registered census is %d, not the registered 96"
                           % len(census))
    shadow = {h["identity_key"]: h for h in _load(RECENSUS)["hotels"]}
    registry = Registry(census)
    answered, _shard = _authority()
    signed = signed_decisions()
    held = holds()
    rulings = {r["identity_key"]: r for r in _load(RULINGS)["rows"]}
    obs = {r["identity_key"]: r for r in _load(OBSERVATIONS)["records"]}

    # -- B / C: signed rows whose disposition is not yet in authority. ------- #
    unapplied, applied_already = [], []
    for key, row in signed.items():
        target, _basis = registry.resolve(row, shadow.get(key))
        want = row["proposes_authority"]
        state = answered.get(target) if target else None
        if state == want or (want == "PUBLISHED_PET_FRIENDLY"
                             and state == "PUBLISHED_PET_FRIENDLY"):
            applied_already.append(key)
            continue
        entry = OrderedDict((
            ("signed_identity_key", key),
            ("canonical_name", row.get("canonical_name")),
            ("brand", row.get("brand")),
            ("proposes_authority", want),
            ("signed_by_work_order", row["signed_by_work_order"]),
            ("bound_source_url", row.get("bound_source_url")),
            ("bound_snapshot_hash", row.get("bound_snapshot_hash")),
            ("held_by_founder", key in held),
        ))
        entry.update(classify(row, shadow.get(key), registry))
        entry["has_owned_observation"] = key in obs
        unapplied.append(entry)

    # -- A / E / F: the founder holds, with the class each ruling puts it in. - #
    hold_rows = []
    for key in held:
        ruling = rulings.get(key) or {}
        hold_rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", ruling.get("canonical_name")),
            ("brand", ruling.get("brand")),
            ("founder_ruling", ruling.get("founder_ruling")),
            ("founder_ruling_note", ruling.get("founder_ruling_note")),
            ("proposed_disposition", ruling.get("proposed_disposition")),
            ("in_registered_census", key in {h["identity_key"] for h in census}),
            ("in_shadow_recensus", key in shadow),
            ("has_owned_observation", key in obs),
            ("already_answered", answered.get(key)),
        )))

    by_label: Dict[str, int] = {}
    for entry in unapplied:
        by_label[entry["label"]] = by_label.get(entry["label"], 0) + 1

    unresolved_partition = [i["identity_key"] for i in
                            _load(_REPO_ROOT / "launch_packages" / "pettripfinder"
                                  / "pittsburgh_final_partition_001.json")["items"]
                            if not i["resolved"]]

    return OrderedDict((
        ("schema", "ptf-market-backlog/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("rebuilt_from",
         "the three committed founder decision ledgers, the committed ruling "
         "ledger, the committed policy package and exclusion shard, the "
         "registered census and the shadow recensus -- not from any prior "
         "run's report."),
        ("registered_census", len(census)),
        ("shadow_recensus", len(shadow)),
        ("signed_total", len(signed)),
        ("signed_already_in_authority", len(applied_already)),
        ("signed_but_unapplied", len(unapplied)),
        ("classification_counts", OrderedDict(sorted(by_label.items()))),
        ("founder_holds", len(hold_rows)),
        ("rows_answered", len(answered)),
        ("rows_still_unresolved", len(unresolved_partition)),
        ("holds", hold_rows),
        ("unapplied", unapplied),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        doc = build()
    except BacklogError as exc:
        print("REFUSED: %s" % exc)
        return 2
    print("registered census        : %d" % doc["registered_census"])
    print("shadow recensus          : %d (not promoted)" % doc["shadow_recensus"])
    print("signed total             : %d" % doc["signed_total"])
    print("  already in authority   : %d" % doc["signed_already_in_authority"])
    print("  signed but unapplied   : %d" % doc["signed_but_unapplied"])
    for label, n in doc["classification_counts"].items():
        print("      %-34s %d" % (label, n))
    print("founder holds            : %d" % doc["founder_holds"])
    print("rows answered            : %d" % doc["rows_answered"])
    print("rows still unresolved    : %d" % doc["rows_still_unresolved"])
    print()
    for entry in doc["unapplied"]:
        print("  %-34s %-52s %s"
              % (entry["label"], entry["signed_identity_key"][:51],
                 entry["proposes_authority"]))
    if not args.write:
        print("(check only -- pass --write)")
        return 0
    REPORTS.mkdir(parents=True, exist_ok=True)
    _write(BACKLOG, doc)
    print("WROTE %s" % BACKLOG.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
