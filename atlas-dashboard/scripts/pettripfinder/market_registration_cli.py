"""Install a market's authority shard from its founder-signed authority.

    python scripts/pettripfinder/market_registration_cli.py \
      --market st-louis-mo \
      --authority launch_packages/pettripfinder/st_louis_mo_proposed_authority_008b.json \
      --write

WHY THIS EXISTS
---------------
``markets/<market_id>.json`` registers a market. It does not give it an
AUTHORITY: the site builds hotel profiles from
``markets/authority/<market_id>/seed_businesses.csv`` joined to the committed
policy package, and ``site_data.verified_public_hotels`` FAILS CLOSED on a
committed policy record with no seed row. Registration without a shard is a
market that raises rather than one that publishes.

Milwaukee derived its shard in ``acquisition/publication_037.py``, which reads
that market's own ledgers by name. This module is the same derivation with no
market in it: everything comes from the ``ptf-market-proposed-authority/1.0``
document the generic signature path already writes, plus the market's identity
census for the one field the authority does not carry (the telephone).

WHAT IT MAY AND MAY NOT DO
--------------------------
* One seed row per PET_FRIENDLY record, and nothing else. A held, refused or
  SUPERSEDED identity has no row to leak -- absence, not suppression.
* One exclusion record per VERIFIED_NO_PETS record, carrying the founder's own
  reviewer id and date. The exclusion contract's ``record_hash`` and
  ``approval_hash`` are DERIVED by ``hotel_exclusions``' own functions, never
  written here, so a hand-edited exclusion fails its own validator.
* Nothing is invented. A record whose authority and census between them state
  no address, no source URL, no observation date or no policy sentence is
  REFUSED BY NAME rather than published with a blank.
* The routing and affiliate shards are created EMPTY, which is what every live
  market that has neither carries. An empty shard is a statement ("this market
  routes nothing, and links to nobody"); a missing one is a silence.

Nothing here publishes and nothing here deploys. Writing a shard makes a
registered market buildable; the founder's launch participation decides whether
it joins a bundle.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE   # noqa: E402
from scripts.pettripfinder import market_authority as MA   # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

AUTHORITY_SCHEMA = "ptf-market-proposed-authority/1.0"
CATEGORY = "pet-friendly-hotels"
SEED_SOURCE_TYPE = "OFFICIAL_PROPERTY"

#: The seed columns a row must actually carry a value for. ``rating``,
#: ``amenities`` and ``canonical`` are blank on every live market's shard.
SEED_REQUIRED = ("name", "address", "city", "state", "postal_code",
                 "website_url", "source_url", "observed_at", "pet_policy")


class MarketRegistrationError(RuntimeError):
    """A record cannot become inventory, and nothing will be invented to fix it."""


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
    return raw or ""


def load_authority(path: Path) -> Dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if doc.get("schema") != AUTHORITY_SCHEMA:
        raise MarketRegistrationError(
            "%s: schema is %r, expected %r" % (path, doc.get("schema"),
                                               AUTHORITY_SCHEMA))
    return doc


def census_by_key(path: Path) -> Dict[str, Dict]:
    doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["hotels"]}


def policy_sentence(record: Mapping) -> str:
    """The property's own words, as the seed row carries them.

    The seed CSV's ``pet_policy`` column is verbatim recorded wording the
    profile renderer shows as evidence. It is the record's own evidence quote,
    never a sentence composed here: a policy this layer wrote would be a claim
    nobody reviewed.
    """
    quote = _flat(record.get("evidence_quote", ""))
    if quote:
        return quote
    for item in record.get("evidence") or ():
        quote = _flat(item.get("quote", ""))
        if quote:
            return quote
    return ""


def seed_row(record: Mapping, census: Mapping, market_id: str,
             package: Optional[Mapping[str, Mapping]] = None) -> Dict[str, str]:
    """One approved authority record as an inventory row, or an error."""
    key = record["normalized_name"]
    # The PUBLISHED name comes from the committed package, which is the
    # identity authority for the public surface (the release contract says so:
    # verified identities are derived from the package at assembly time). Taking
    # it from the authority instead would let the two disagree, and the one
    # place they disagree is exactly where an evidence-cited name correction
    # replaced a bare chain word -- the case the join cannot survive.
    published = (package or {}).get(key) or {}
    row = OrderedDict((column, "") for column in MA.SEED_COLUMNS)
    row.update({
        "name": published.get("name") or record["canonical_name"],
        "category": CATEGORY,
        "address": record.get("address", "") or census.get("address", ""),
        "city": record.get("city", "") or census.get("city", ""),
        "state": record.get("state", "") or census.get("state", ""),
        "postal_code": record.get("postal_code", "") or census.get("postal_code", ""),
        # The telephone is the ONE field the signed authority does not carry.
        "phone": _phone(census.get("phone", "")),
        "website_url": (record.get("official_url", "")
                        or census.get("official_url", "")
                        or record.get("source_url", "")),
        "source_url": record.get("source_url", ""),
        "source_type": SEED_SOURCE_TYPE,
        "observed_at": (record.get("observed_at") or "")[:10],
        "pet_policy": policy_sentence(record),
        "market_id": market_id,
    })
    missing = [c for c in SEED_REQUIRED if not str(row[c]).strip()]
    if missing:
        raise MarketRegistrationError(
            "%s cannot become inventory: the signed authority and the census "
            "between them state no %s, and this layer does not invent one"
            % (key, ", ".join(missing)))
    # The join this row has to survive is site_data.verified_public_hotels:
    # normalize_name(seed name) must equal the package record's ``key``. That is
    # NOT always the census identity key -- a founder-authorised name correction
    # replaces a bare chain word with the building the page names -- so the
    # check is made against the committed package, never against the identity.
    if package is not None:
        expected = published.get("key")
        if expected is None:
            raise MarketRegistrationError(
                "%s is approved but the committed policy package has no record "
                "for it, so the row would publish with no verified policy" % key)
        if normalize_name(row["name"]) != expected:
            raise MarketRegistrationError(
                "%s: the seed row's name normalises to %r and the package joins "
                "on %r -- the two must agree or the join fails closed"
                % (key, normalize_name(row["name"]), expected))
    return row


def seed_rows(authority: Mapping, census: Mapping[str, Dict], market_id: str,
              package: Optional[Mapping[str, Mapping]] = None
              ) -> List[Dict[str, str]]:
    rows = []
    for record in sorted(authority["pet_friendly"],
                         key=lambda r: r["normalized_name"]):
        key = record["normalized_name"]
        if key not in census:
            raise MarketRegistrationError("%s is not in the identity census" % key)
        rows.append(seed_row(record, census[key], market_id, package))
    return rows


def package_records(market_id: str) -> Dict[str, Dict]:
    """``identity_key -> committed package record`` for this market.

    Absent package: an empty map, and the seed builder falls back to the
    authority's own name and runs no join check -- registration must be
    possible before a package exists. The check is what makes registration WITH
    one meaningful.
    """
    from scripts.pettripfinder.site_data import published_facts_path
    path = published_facts_path(market_id)
    if not path.is_file():
        return {}
    package = json.loads(path.read_text(encoding="utf-8-sig"))
    return {h.get("identity_key") or h["key"]: h
            for h in package.get("hotels") or ()}


def exclusion_record(record: Mapping, census: Mapping, market_id: str,
                     *, decision_source: Mapping) -> Dict:
    """One VERIFIED_NO_PETS authority row as an exclusion-contract record.

    ``record_hash`` and ``approval_hash`` are computed by ``hotel_exclusions``'
    own functions over the fields it names, so the shard validates under the
    same rule every other market's does.
    """
    key = record["normalized_name"]
    context = ""
    for item in record.get("evidence") or ():
        text = _flat(item.get("context", "") or item.get("quote", ""))
        if len(text) > len(context):
            context = text
    out = OrderedDict([
        ("exclusion_id", record["exclusion_id"]),
        ("canonical_name", record["canonical_name"]),
        # DERIVED from the canonical name this record carries, not copied from
        # the authority's identity key. They are the same string for every row
        # whose census name was never corrected, and they differ for a row that
        # was: Louisville's "days inn" publishes as "Days Inn & Suites by
        # Wyndham Louisville SW", and the exclusion contract requires the
        # normalized name to derive from the canonical one -- which is also how
        # the publication guard matches, since it normalises the name on the row
        # it is about to publish. Copying the key made the contract's own rule
        # fail on exactly the rows a name correction improved
        # (PTF-LOUISVILLE-PUBLICATION-008).
        ("normalized_name", normalize_name(record["canonical_name"])),
        ("address", record.get("address", "") or census.get("address", "")),
        ("city", record.get("city", "") or census.get("city", "")),
        ("state", record.get("state", "") or census.get("state", "")),
        ("postal_code", record.get("postal_code", "") or census.get("postal_code", "")),
        ("official_url", record.get("official_url", "") or record.get("source_url", "")),
        ("exclusion_state", record["exclusion_state"]),
        ("evidence_quote", _flat(record.get("evidence_quote", ""))),
        ("evidence_context", context),
        ("source_url", record.get("source_url", "")),
        ("observed_at", (record.get("observed_at") or "")[:10]),
        # The document the reader actually parsed, in the contract's prefixed
        # form. It is the record's own snapshot, not a hash computed here.
        ("source_hash", "sha256:%s" % record["snapshot_hash"]),
        ("reviewer_id", record["founder_reviewer_id"]),
        ("reviewed_at", record["founder_reviewed_at"]),
        ("notes", "affirmative refusal on the property's own page; a "
                  "service-animal statement is a legal access category and is "
                  "never read as a pet permission or as a refusal on its own"),
        ("market_id", market_id),
        ("decision_source", OrderedDict(decision_source)),
    ])
    if out["normalized_name"] != normalize_name(out["canonical_name"]):
        raise MarketRegistrationError(
            "%s: normalized_name does not derive from canonical_name" % key)
    missing = [f for f in HE.REQUIRED_FIELDS
               if f not in ("record_hash", "approval_hash")
               and not str(out.get(f, "")).strip()]
    if missing:
        raise MarketRegistrationError(
            "%s cannot become an exclusion: no %s stated, and this layer does "
            "not invent one" % (key, ", ".join(missing)))
    out["record_hash"] = HE.record_hash(out)
    out["approval_hash"] = HE.approval_hash(out)
    return out


def exclusion_records(authority: Mapping, census: Mapping[str, Dict],
                      market_id: str) -> List[Dict]:
    built = authority.get("built_from") or {}
    source = OrderedDict([
        ("work_order", authority.get("work_order", "")),
        ("ledgers", list(built.get("source_ledgers") or ())),
        ("decided_by", built.get("decided_by", "")),
        ("decision_basis", "founder signature over this row in the named "
                           "ledger; the exclusion restates that ruling and "
                           "adds no finding of its own"),
    ])
    records = []
    for record in sorted(authority["verified_no_pets"],
                         key=lambda r: r["normalized_name"]):
        key = record["normalized_name"]
        records.append(exclusion_record(record, census.get(key, {}), market_id,
                                        decision_source=source))
    return records


def affiliate_shard(market_id: str) -> Dict:
    """An EMPTY affiliate shard, in the shape every live market's carries."""
    reference = json.loads(
        (MA.AUTHORITY_DIR / "pittsburgh-pa" / MA.AFFILIATE_SHARD_NAME)
        .read_text(encoding="utf-8-sig"))
    return OrderedDict([
        ("schema", reference["schema"]),
        ("contract", reference["contract"]),
        ("market_id", market_id),
        ("note", reference["note"]),
        ("count", 0),
        ("destinations", []),
    ])


def build(market_id: str, authority_path: Path, census_path: Path) -> Dict:
    """Every shard document this market's authority implies, unwritten."""
    authority = load_authority(authority_path)
    if authority["market_id"] != market_id:
        raise MarketRegistrationError(
            "%s is the authority for %r, not %r"
            % (authority_path, authority["market_id"], market_id))
    census = census_by_key(census_path)
    rows = seed_rows(authority, census, market_id,
                     package_records(market_id))
    exclusions = exclusion_records(authority, census, market_id)
    if len(rows) != authority["pet_friendly_count"]:
        raise MarketRegistrationError(
            "derived %d seed rows from %d pet-friendly records"
            % (len(rows), authority["pet_friendly_count"]))
    if len(exclusions) != authority["verified_no_pets_count"]:
        raise MarketRegistrationError(
            "derived %d exclusions from %d verified-no-pets records"
            % (len(exclusions), authority["verified_no_pets_count"]))
    return OrderedDict([
        ("market_id", market_id),
        ("seed_rows", rows),
        ("exclusions_document", MA.build_exclusions_shard(market_id, exclusions)),
        ("routing_document", MA.build_routing_shard(market_id, [])),
        ("affiliate_document", affiliate_shard(market_id)),
        ("authority_total", authority["authority_total"]),
    ])


def write(built: Mapping) -> List[str]:
    market_id = built["market_id"]
    written = []
    pairs = (
        (MA.seed_shard_path(market_id), MA.render_seed_csv(built["seed_rows"])),
        (MA.exclusions_shard_path(market_id),
         MA.render_json(built["exclusions_document"])),
        (MA.routing_shard_path(market_id),
         MA.render_json(built["routing_document"])),
        (MA.affiliate_shard_path(market_id),
         MA.render_json(built["affiliate_document"])),
    )
    for path, text in pairs:
        if MA._write_if_changed(path, text):
            written.append(path.relative_to(_REPO_ROOT).as_posix())
    return written


def verify(market_id: str, authority_path: Path) -> List[str]:
    """The written shard states exactly the current signed-minus-superseded set."""
    authority = load_authority(authority_path)
    problems: List[str] = []
    pf = {r["normalized_name"] for r in authority["pet_friendly"]}
    np = {r["normalized_name"] for r in authority["verified_no_pets"]}
    superseded = {r["identity_key"] for r in authority.get("superseded_rows") or ()}

    # A seed row is identified by the key it JOINS on, which the package owns.
    # Comparing it to the identity set directly would report the three
    # founder-authorised name corrections as a disagreement.
    identity_of = {h["key"]: k for k, h in package_records(market_id).items()}
    seeds = {identity_of.get(normalize_name(r["name"]), normalize_name(r["name"]))
             for r in MA.load_market_seed_rows(market_id)}
    # The same correction, on the other side. An exclusion has no package row to
    # join through, and its normalized_name DERIVES from the canonical name the
    # record carries -- which the exclusion contract requires. So the authority's
    # no-pets set is compared through the same derivation rather than through the
    # census identity key, which is what a name correction changes
    # (PTF-LOUISVILLE-PUBLICATION-008).
    np_derived = {normalize_name(r["canonical_name"])
                  for r in authority["verified_no_pets"]}
    excl = {r["normalized_name"] for r in MA.load_market_exclusions(market_id)}
    if seeds != pf:
        problems.append("seed shard disagrees with the authority's pet-friendly "
                        "set: %s" % sorted(seeds ^ pf)[:5])
    if excl != np_derived:
        problems.append("exclusion shard disagrees with the authority's "
                        "verified-no-pets set: %s" % sorted(excl ^ np_derived)[:5])
    leaked = sorted((seeds | excl) & superseded)
    if leaked:
        problems.append("a SUPERSEDED identity reached a publication set: %s" % leaked)
    if len(seeds) + len(excl) != authority["authority_total"]:
        problems.append("shard states %d identities, the authority states %d"
                        % (len(seeds) + len(excl), authority["authority_total"]))
    for row in MA.load_market_exclusions(market_id):
        if row["exclusion_state"] != HE.VERIFIED_NO_PETS:
            problems.append("%s is %s, not VERIFIED_NO_PETS"
                            % (row["exclusion_id"], row["exclusion_state"]))
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--authority", required=True, type=Path)
    parser.add_argument("--census", type=Path,
                        help="defaults to the market's committed identity census")
    parser.add_argument("--write", action="store_true",
                        help="without it, derive and report and write nothing")
    args = parser.parse_args(argv)

    census = args.census or (MA.LAUNCH_PACKAGE / "identity_census"
                             / ("%s.json" % args.market))
    built = build(args.market, args.authority, census)
    print("market            :", args.market)
    print("seed rows         :", len(built["seed_rows"]))
    print("exclusions        :", built["exclusions_document"]["count"])
    print("routing records   :", built["routing_document"]["count"])
    print("affiliate rows    :", built["affiliate_document"]["count"])
    print("authority total   :", built["authority_total"])
    if not args.write:
        print("nothing written (pass --write)")
        return 0
    for path in write(built):
        print("wrote             :", path)
    problems = verify(args.market, args.authority)
    for problem in problems:
        print("PROBLEM           :", problem)
    return 1 if problems else 0


if __name__ == "__main__":                      # pragma: no cover
    raise SystemExit(main())
