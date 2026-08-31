# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-IDENTITY-CLOSE-007 Phase 1 -- the three authorised identity rulings.

    python -m scripts.pettripfinder.pittsburgh_identity_close_007
    python -m scripts.pettripfinder.pittsburgh_identity_close_007 --write

These three were presented in Order 006, came back blank in the UI, and were not
applied. Order 007 authorises them explicitly. Each is rebuilt from the committed
evidence rather than from 006's report, and each artifact's SHA-256 is re-derived
and checked against the snapshot the observation names before anything is written.

1. COURTYARD -- SAME_IDENTITY_SUPERSESSION, NO NEW CENSUS ROW
   The registered stub "Courtyard by Marriott Pittsburgh Waterfront" (GPHA
   directory, ZIP 15120, no address, phone or URL) IS the property Marriott
   calls "Courtyard by Marriott Pittsburgh West Homestead/Waterfront" (PITHW,
   401 West Waterfront Drive, 15120). The stub absorbs the first-party facts and
   becomes a refusal.

   Its identity_key and canonical_name are DELIBERATELY unchanged. An exclusion's
   normalized_name must derive from its canonical_name, and
   normalize_name("...West Homestead/Waterfront") is not
   "courtyard by marriott pittsburgh waterfront" -- renaming the row in place
   would break the derivation the registry checks. The Marriott form is recorded
   in the name-correction overlay instead, which is exactly the display layer
   that overlay exists to be, and prior provenance is preserved verbatim.

2. COMFORT SUITES -- AUTHORISED IDENTITY-KEY CORRECTION, THEN ADD
   The bare key "comfort suites" is a chain word Indianapolis already holds, so
   Order 005 refused the add on the key collision. The founder has now authorised
   the correction to the name Choice states in its own page title, JSON-LD and
   H1: "Comfort Suites Monroeville - Pittsburgh East". That name derives the key
   "comfort suites monroeville pittsburgh east", which collides with nothing in
   any market. The bare key is NOT reused.

3. INTOWN SUITES -- TRUE_CENSUS_ADD
   Proven first-party: the policy sentence itself names the property, and the
   page states 4595 McKnight Road and a local phone. The generic page <title>
   that tripped the M10 membrane is InTown's site chrome, not the property's name.

ADD, NEVER DOWNGRADE
---------------------
Two rows are added and none is removed: every one of the 101 prior identities is
asserted byte-identical afterwards, except the Courtyard stub, whose ONLY
permitted movement is the enrichment named above.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE                  # noqa: E402
from scripts.pettripfinder import market_authority as MA                  # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT     # noqa: E402
from scripts.pettripfinder.contracts.identity_key import (                # noqa: E402
    is_canonical_key, ptf_identity_key)
from scripts.pettripfinder.site_data import normalize_name                # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, OBSERVATIONS, OVERLAY, PACKAGE, RECENSUS, REPORTS,
    _load, _write, canonical_url, digits, property_codes, street)

WORK_ORDER = "PTF-PITTSBURGH-IDENTITY-CLOSE-007"
AS_OF = "2026-08-31"
REVIEWER = "PTF-FOUNDER-001"
OPERATOR = "jfields80"
CORPUS = (_REPO_ROOT / "data" / "acquisition"
          / "pittsburgh_pa_factory_recensus_001" / "pass1")
LEDGER = REPORTS / "pittsburgh_identity_close_007_rulings.json"

SUPERSEDE = OrderedDict((
    ("held_row", "courtyard by marriott pittsburgh west homestead waterfront"),
    ("registered_target", "courtyard by marriott pittsburgh waterfront"),
    ("display_name", "Courtyard by Marriott Pittsburgh West Homestead/Waterfront"),
    ("slug", "courtyard-by-marriott-pittsburgh-west-homestead-waterfront"),
    ("expect_code", "marriott:pithw"),
    ("expect_address", "401 West Waterfront Drive"),
    ("expect_postal", "15120"),
))
RENAME = OrderedDict((
    ("held_row", "comfort suites"),
    ("new_canonical_name", "Comfort Suites Monroeville - Pittsburgh East"),
    ("slug", "comfort-suites"),
    ("expect_code", "choice:pa392"),
    ("expect_address", "2731 Mosside Boulevard"),
    ("expect_postal", "15146"),
))
ADD = OrderedDict((
    ("held_row", "intown suites extended stay pittsburgh pa"),
    ("slug", "intown-suites-extended-stay-pittsburgh-pa"),
    ("expect_address", "4595 McKnight Road"),
    ("expect_postal", "15237"),
    ("phone_from_page", "(412) 931-6624"),
))

CENSUS_FIELDS = (
    "identity_key", "canonical_name", "display_name", "slug", "market_id",
    "address", "city", "state", "postal_code", "phone", "identity_state",
    "lodging_state", "policy_state", "collision_state", "official_url",
    "corridor", "normalized_name", "observed_at", "provenance", "source",
    "source_id", "street_identity", "url_shape", "assignment_basis",
    "assignment_value", "disposition", "former_name",
)


class CloseError(RuntimeError):
    pass


def _page(slug: str) -> Tuple[Path, str]:
    found = sorted((CORPUS / slug).rglob("rendered.html"))
    if not found:
        raise CloseError("no owned page under %s" % slug)
    return found[0], hashlib.sha256(found[0].read_bytes()).hexdigest()


def _checked_observation(key: str, slug: str, obs: Mapping) -> Dict:
    """The observation, with its artifact re-hashed and re-bound."""
    record = obs.get(key)
    if record is None:
        raise CloseError("%s has no owned observation" % key)
    _path, digest = _page(slug)
    stated = record["observation"].get("snapshot_hash")
    if stated != digest:
        raise CloseError("%s: the retained page no longer hashes to the "
                         "snapshot the observation names (%s vs %s)"
                         % (key, stated, digest))
    if record["observation"]["extraction"].get("pets_allowed") is not False:
        raise CloseError("%s: the evidence does not state a refusal" % key)
    return record


def _census_row(shadow: Mapping, template: Mapping, *, key: str,
                canonical: str, phone: str = "") -> Dict:
    out = OrderedDict()
    for field in CENSUS_FIELDS:
        if field == "identity_key":
            out[field] = key
        elif field in ("canonical_name", "display_name"):
            out[field] = canonical
        elif field == "normalized_name":
            out[field] = normalize_name(canonical)
        elif field == "slug":
            out[field] = canonical.lower().replace("/", "-").replace(" ", "-")
        elif field == "phone" and phone:
            out[field] = phone
        elif field == "street_identity":
            addr = str(shadow.get("address") or "").strip().lower()
            zipc = str(shadow.get("postal_code") or "").strip()
            out[field] = "%s|%s" % (addr, zipc) if addr and zipc else ""
        elif field == "url_shape":
            out[field] = "OFFICIAL_PROPERTY_PAGE" if shadow.get("official_url") else ""
        elif field in ("disposition", "former_name"):
            out[field] = ""
        elif field in shadow:
            out[field] = shadow[field]
        else:
            out[field] = template.get(field, "")
    out["policy_state"] = "POLICY_NOT_VERIFIED"
    out["identity_state"] = "IDENTITY_CONFIRMED"
    if out["normalized_name"] != key:
        raise CloseError("%s: normalized_name %r does not derive the key"
                         % (key, out["normalized_name"]))
    return out


def _exclusion(key: str, canonical: str, row: Mapping, record: Mapping,
               ruling: str, digest: str) -> Dict:
    source = record["observation"]
    quote = None
    for entry in record["publication_grade"]["evidence_entries"]:
        if entry.get("field") == "pets_allowed":
            quote = entry["quote"]
            break
    if not quote:
        raise CloseError("%s: a refusal needs the sentence that refuses" % key)
    for field in ("address", "city", "state", "postal_code"):
        if not str(row.get(field) or "").strip():
            raise CloseError("%s: an exclusion needs %s" % (key, field))
    out = OrderedDict((
        ("exclusion_id", "pgh-%s" % key.replace(" ", "-")),
        ("canonical_name", canonical),
        ("normalized_name", key),
        ("address", row["address"]), ("city", row["city"]),
        ("state", row["state"]), ("postal_code", row["postal_code"]),
        ("official_url", source["source_url"]),
        ("exclusion_state", HE.VERIFIED_NO_PETS),
        ("evidence_quote", quote),
        ("source_url", source["source_url"]),
        ("observed_at", source["observed_at"]),
        ("source_hash", "sha256:%s" % digest),
        ("reviewer_id", OPERATOR), ("reviewed_at", AS_OF),
        ("notes", ruling),
        ("market_id", MARKET_ID),
    ))
    out["record_hash"] = HE.record_hash(out)
    out["approval_hash"] = HE.approval_hash(out)
    return out


def build():
    census = _load(CENSUS)
    rows = {h["identity_key"]: h for h in census["hotels"]}
    shadow = {h["identity_key"]: h for h in _load(RECENSUS)["hotels"]}
    obs = {r["identity_key"]: r for r in _load(OBSERVATIONS)["records"]}
    published = {h["identity_key"] for h in _load(PACKAGE)["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"]}
    before = len(census["hotels"])

    out = json.loads(json.dumps(census))
    by_key = {h["identity_key"]: h for h in out["hotels"]}
    exclusions, applied = [], []

    # -- 1. Courtyard supersession: enrich in place, no new row --------------- #
    src = shadow[SUPERSEDE["held_row"]]
    record = _checked_observation(SUPERSEDE["held_row"], SUPERSEDE["slug"], obs)
    _p, digest = _page(SUPERSEDE["slug"])
    if SUPERSEDE["expect_code"] not in property_codes(src.get("official_url")):
        raise CloseError("courtyard: the ruling's property code is not on the row")
    if street(src.get("address")) != street(SUPERSEDE["expect_address"]):
        raise CloseError("courtyard: the ruling's address is not on the row")
    target = by_key[SUPERSEDE["registered_target"]]
    if str(target.get("postal_code") or "") != SUPERSEDE["expect_postal"]:
        raise CloseError("courtyard: the registered stub is not at the ruling's ZIP")
    for field in ("address", "phone", "official_url"):
        if str(target.get(field) or "").strip():
            raise CloseError("courtyard: the stub already states %s; this "
                             "supersession only fills what the stub lacks" % field)
    prior = OrderedDict((k, target.get(k)) for k in
                        ("source", "source_id", "provenance", "observed_at",
                         "identity_state", "canonical_name"))
    target["address"] = src["address"]
    target["phone"] = src["phone"]
    target["official_url"] = src["official_url"]
    target["street_identity"] = "%s|%s" % (str(src["address"]).lower(),
                                           src["postal_code"])
    target["url_shape"] = "OFFICIAL_PROPERTY_PAGE"
    target["identity_state"] = "IDENTITY_CONFIRMED"
    target["former_name"] = ""
    exclusions.append(_exclusion(
        SUPERSEDE["registered_target"], target["canonical_name"], target, record,
        "FOUNDER RULING (SAME_IDENTITY_SUPERSESSION) %s: the registered stub, "
        "sourced from the GPHA directory with no address, phone or URL, IS the "
        "property Marriott calls %r (%s). Only one Courtyard exists at ZIP %s in "
        "either census and nothing on the stub contradicts. The stub absorbed the "
        "first-party facts; its identity_key and canonical_name are unchanged so "
        "normalized_name still derives, and the Marriott form is recorded in the "
        "name-correction overlay, which is a DISPLAY layer. Prior provenance "
        "preserved: %s. Provider calls 0, spend $0.00."
        % (WORK_ORDER, SUPERSEDE["display_name"], SUPERSEDE["expect_code"],
           SUPERSEDE["expect_postal"], json.dumps(prior)), digest))
    applied.append(OrderedDict((
        ("ruling", "SAME_IDENTITY_SUPERSESSION"),
        ("held_row", SUPERSEDE["held_row"]),
        ("registered_identity", SUPERSEDE["registered_target"]),
        ("census_rows_added", 0),
        ("display_name_overlay", SUPERSEDE["display_name"]),
        ("prior_provenance", prior),
        ("artifact_sha256", "sha256:%s" % digest))))

    # -- 2. Comfort Suites: authorised key correction, then add -------------- #
    src = shadow[RENAME["held_row"]]
    record = _checked_observation(RENAME["held_row"], RENAME["slug"], obs)
    _p, digest = _page(RENAME["slug"])
    check = record["observation"]["identity_check"]
    if check.get("name_on_page") != RENAME["new_canonical_name"]:
        raise CloseError("comfort suites: the page no longer states the "
                         "canonical name the ruling adopts")
    if RENAME["expect_code"] not in property_codes(src.get("official_url")):
        raise CloseError("comfort suites: the ruling's Choice code is not on the row")
    key = ptf_identity_key(RENAME["new_canonical_name"])
    if not is_canonical_key(key):
        raise CloseError("comfort suites: %r is not a canonical key" % key)
    if key in by_key or key == RENAME["held_row"]:
        raise CloseError("comfort suites: the corrected key is not new")
    row = _census_row(src, census["hotels"][0], key=key,
                      canonical=RENAME["new_canonical_name"])
    row["former_name"] = src["canonical_name"]
    out["hotels"].append(row)
    by_key[key] = row
    exclusions.append(_exclusion(
        key, RENAME["new_canonical_name"], row, record,
        "FOUNDER RULING (AUTHORISED IDENTITY-KEY CORRECTION + TRUE_CENSUS_ADD) "
        "%s: the signed key 'comfort suites' is a bare chain word Indianapolis "
        "already holds as an identity key, so PTF-PITTSBURGH-FOUNDER-HOLD-"
        "RESOLUTION-005 refused the add on that collision. Choice states this "
        "property's canonical name in its own page title, JSON-LD and H1; that "
        "name derives %r, which collides with nothing in any market. The bare "
        "key is not reused. Provider calls 0, spend $0.00."
        % (WORK_ORDER, key), digest))
    applied.append(OrderedDict((
        ("ruling", "IDENTITY_KEY_CORRECTION + TRUE_CENSUS_ADD"),
        ("held_row", RENAME["held_row"]), ("new_identity_key", key),
        ("new_canonical_name", RENAME["new_canonical_name"]),
        ("census_rows_added", 1), ("property_code", RENAME["expect_code"]),
        ("artifact_sha256", "sha256:%s" % digest))))

    # -- 3. InTown Suites: census add ---------------------------------------- #
    src = shadow[ADD["held_row"]]
    record = _checked_observation(ADD["held_row"], ADD["slug"], obs)
    _p, digest = _page(ADD["slug"])
    if street(src.get("address")) != street(ADD["expect_address"]):
        raise CloseError("intown: the ruling's address is not on the row")
    key = ADD["held_row"]
    if key in by_key:
        raise CloseError("intown: already a registered identity")
    row = _census_row(src, census["hotels"][0], key=key,
                      canonical=src["canonical_name"],
                      phone=ADD["phone_from_page"])
    out["hotels"].append(row)
    by_key[key] = row
    exclusions.append(_exclusion(
        key, src["canonical_name"], row, record,
        "FOUNDER RULING (TRUE_CENSUS_ADD + VERIFIED_NO_PETS) %s: proven "
        "first-party -- the policy sentence itself names the property, and the "
        "page states %s and a local phone. The generic page title that tripped "
        "the M10 membrane is InTown's site chrome, not the property's name. No "
        "registered twin and no cross-market collision. Provider calls 0, spend "
        "$0.00." % (WORK_ORDER, ADD["expect_address"]), digest))
    applied.append(OrderedDict((
        ("ruling", "TRUE_CENSUS_ADD + VERIFIED_NO_PETS"),
        ("held_row", key), ("census_rows_added", 1),
        ("artifact_sha256", "sha256:%s" % digest))))

    # -- guards -------------------------------------------------------------- #
    keys = [h["identity_key"] for h in out["hotels"]]
    if len(set(keys)) != len(keys):
        raise CloseError("the rulings created a duplicate identity_key")
    if len(out["hotels"]) != before + 2:
        raise CloseError("expected exactly two new census rows, got %d"
                         % (len(out["hotels"]) - before))
    prior_rows = {h["identity_key"]: json.dumps(h, sort_keys=True)
                  for h in census["hotels"]}
    now_rows = {h["identity_key"]: json.dumps(h, sort_keys=True)
                for h in out["hotels"]}
    missing = sorted(set(prior_rows) - set(now_rows))
    if missing:
        raise CloseError("ADD-NEVER-DOWNGRADE violated: %s" % missing[:5])
    moved = sorted(k for k in prior_rows
                   if prior_rows[k] != now_rows[k]
                   and k != SUPERSEDE["registered_target"])
    if moved:
        raise CloseError("a prior identity moved that this order may not touch: "
                         "%s" % moved[:5])
    ex_keys = [e["normalized_name"] for e in exclusions]
    if len(set(ex_keys)) != len(ex_keys):
        raise CloseError("one identity would be excluded twice")
    if set(ex_keys) & published:
        raise CloseError("an identity would be published AND excluded")
    if set(ex_keys) & excluded:
        raise CloseError("an identity is already excluded")

    out["count"] = len(out["hotels"])
    states: Dict[str, int] = {}
    for hotel in out["hotels"]:
        states[hotel.get("identity_state", "")] = states.get(
            hotel.get("identity_state", ""), 0) + 1
    if "identity_state_counts" in out:
        out["identity_state_counts"] = OrderedDict(sorted(states.items()))
    issues = CENSUS_CONTRACT.validate(out, market_states=["PA"])
    if issues:
        raise CloseError("the census does not validate: %s" % list(issues)[:5])

    shard["exclusions"] = list(shard["exclusions"]) + exclusions
    shard["count"] = len(shard["exclusions"])
    HE.validate(shard)

    overlay = _load(OVERLAY) if OVERLAY.is_file() else {"records": []}
    if not any(r["identity_key"] == SUPERSEDE["registered_target"]
               for r in overlay["records"]):
        overlay["records"].append(OrderedDict((
            ("identity_key", SUPERSEDE["registered_target"]),
            ("census_canonical_name", by_key[SUPERSEDE["registered_target"]]["canonical_name"]),
            ("corrected_canonical_name", SUPERSEDE["display_name"]),
            ("evidence_field", "identity_check.name_on_page"),
            ("source_url", shadow[SUPERSEDE["held_row"]]["official_url"]),
            ("why", "the census name came from a membership directory that "
                    "shortens names; this is the name Marriott's own property "
                    "page states, adopted under %s" % WORK_ORDER),
        )))
        overlay["count"] = len(overlay["records"])
    return out, shard, overlay, exclusions, applied, before


def run(write: bool) -> int:
    census, shard, overlay, exclusions, applied, before = build()
    print("census before        : %d" % before)
    print("census after         : %d (+%d)" % (census["count"], census["count"] - before))
    print("exclusions added     : %d" % len(exclusions))
    for row in applied:
        print("   %-38s %s" % (row["ruling"][:37], row["held_row"][:48]))
    print("exclusion shard after: %d" % shard["count"])
    print("display overlay rows : %d" % overlay.get("count", len(overlay["records"])))
    if not write:
        print("(check only -- pass --write)")
        return 0
    _write(CENSUS, census)
    print("WROTE %s" % CENSUS.name)
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE exclusions shard (%d rows)" % shard["count"])
    _write(OVERLAY, overlay)
    print("WROTE %s" % OVERLAY.name)
    _write(LEDGER, OrderedDict((
        ("schema", "ptf-founder-identity-rulings/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("ruled_by", REVIEWER), ("recorded_by", "Claude Opus 5 (agent transcription)"),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("what_this_is",
         "Three identity rulings presented in PTF-PITTSBURGH-IDENTITY-AND-"
         "RECAPTURE-006, returned blank by the UI and therefore not applied, "
         "then explicitly authorised in this order. Every artifact was "
         "re-hashed and re-bound to the snapshot its observation names before "
         "anything was written."),
        ("census_before", before), ("census_after", census["count"]),
        ("count", len(applied)), ("rulings", applied))))
    print("WROTE %s" % LEDGER.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except CloseError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
