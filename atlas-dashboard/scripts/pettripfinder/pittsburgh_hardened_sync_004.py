# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phases 7-8 -- reconcile twins, apply the 32 signed decisions.

    python -m scripts.pettripfinder.pittsburgh_hardened_sync_004
    python -m scripts.pettripfinder.pittsburgh_hardened_sync_004 --write

WHAT IS STRANDED AND WHY IT CANNOT SIMPLY BE COPIED
----------------------------------------------------
Three founder ledgers hold 32 signed dispositions for Pittsburgh (8 + 21 + 3),
23 APPROVE_PET_FRIENDLY and 9 APPROVE_VERIFIED_NO_PETS. They were signed against
the 115-row SHADOW recensus, and the registered census is still the 96.

So a signed row's ``identity_key`` is not automatically an identity this market
has. Sixteen of the 32 are recensus-only keys. The order forbids promoting the
115 -- the shadow census failed to rediscover live published properties, and a
naive promotion would evict valid authority -- so each recensus-only key has to
be RECONCILED onto the registered identity it actually names, or else left
unapplied. It is never renamed into one on a name resemblance.

THE RECONCILIATION IS BY PROOF, NOT BY NAME
--------------------------------------------
"Near misses at the right postal were mostly DIFFERENT HOTELS" is a lesson this
corpus paid for. A twin is therefore accepted only on evidence that a duplicate
street identity cannot see:

  OFFICIAL_URL     the signed row's bound source URL IS a registered row's URL
  PROPERTY_CODE    same brand-scoped property code (marriott:pityu, hilton:...)
  ADDRESS+PHONE    same street address AND same phone
  POSTAL+BRAND     same postal, same brand, and the registered name is a strict
                   prefix of the signed name (a degraded census stub)

Anything else is UNBINDABLE and is reported, not guessed. Six signed rows land
there: their property codes, addresses and phones collide with nothing in the
registered 96, so they are genuinely absent identities. Applying them would be a
census ADD, which Phase 4 of this order reserves for a separate SUPERSEDE /
ADD-NEVER-DOWNGRADE work order. They stay unapplied and are named in the report.

THE FOUNDER ALREADY RULED THE HARD ONES
-----------------------------------------
Two reconciliations retire a twin rather than merge into a peer, and neither is
this module's judgement: ``pittsburgh_pa_founder_rulings_003`` records
DUPLICATE_PRESERVED_QUALIFIED_IDENTITY on the signed row and RETIRED_STALE_TWIN
on the other, with "supersede" written in the founder's own note. This module
asserts that pairing and refuses if it ever stops matching.

NOTHING HERE IS RE-ASKED
-------------------------
Every record this writes carries the founder's decision, the work order that
signed it, and the bound snapshot hash the signature names. No disposition is
re-derived, widened or defaulted; the nine HOLD rows are untouched.
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

from scripts.pettripfinder import hotel_exclusions as HE          # noqa: E402
from scripts.pettripfinder import market_authority as MA          # noqa: E402
from scripts.pettripfinder import policy_migration as PM          # noqa: E402
from scripts.pettripfinder.contracts import enums                 # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify  # noqa: E402
from scripts.pettripfinder.market_policy_package_cli import (     # noqa: E402
    corrected_names, project_facts)

WORK_ORDER = "PTF-PITTSBURGH-HARDENED-SYNC-004"
MARKET_ID = "pittsburgh-pa"
MARKET_NAME = "Pittsburgh, PA"
AS_OF = "2026-08-30"
REVIEWER = "PTF-FOUNDER-001"
OPERATOR = "jfields80"

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE_DIR / "markets" / "reports"
PACKAGE = PACKAGE_DIR / ("hotel_policy_facts_%s.json" % MARKET_ID)
CENSUS = PACKAGE_DIR / "identity_census" / ("%s.json" % MARKET_ID)
RECENSUS = PACKAGE_DIR / "identity_census" / "recensus" / ("%s.json" % MARKET_ID)
OVERLAY = PACKAGE_DIR / "markets" / "name_corrections" / ("%s.json" % MARKET_ID)
OBSERVATIONS = PACKAGE_DIR / "pittsburgh_pa_observation_store_recensus_001.json"
RULINGS = PACKAGE_DIR / "pittsburgh_pa_founder_rulings_003.json"
DECISIONS = (
    (PACKAGE_DIR / "pittsburgh_pa_founder_decisions_recensus_001.json",
     "PTF-PITTSBURGH-FOUNDER-REVIEW-RECENSUS-001"),
    (PACKAGE_DIR / "pittsburgh_pa_founder_decisions_002.json",
     "PTF-PITTSBURGH-FOUNDER-EXCEPTION-RULINGS-002"),
    (PACKAGE_DIR / "pittsburgh_pa_founder_decisions_003.json",
     "PTF-PITTSBURGH-FOUNDER-CANONICAL-NAME-CORRECTIONS-003"),
)
RECONCILIATION = REPORTS / "pittsburgh_hardened_sync_004_reconciliation.json"
APPLICATION = REPORTS / "pittsburgh_hardened_sync_004_application.json"

#: The founder's own supersessions, asserted against the ruling ledger rather
#: than trusted: signed row -> the twin its note retires.
FOUNDER_SUPERSESSIONS = {
    "courtyard pittsburgh university center":
        "courtyard by marriott pittsburgh university center",
    "hampton inn pittsburgh university medical center":
        "hampton inn university center",
}

PUBLISH = "PUBLISHED_PET_FRIENDLY"
REFUSE = "VERIFIED_NO_PETS"


class SyncError(RuntimeError):
    """The sync found something it must not resolve on its own."""


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: Mapping) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# Identity proof.
# --------------------------------------------------------------------------- #

_CODE_PATTERNS = (
    ("marriott", re.compile(r"marriott\.com/(?:en-us/)?hotels/(?:travel/)?([a-z0-9]{5,7})[-/]")),
    ("marriott", re.compile(r"marriott\.com/([a-z0-9]{5,6})/?$")),
    ("hilton", re.compile(r"hilton\.com/en/hotels/([a-z0-9]+)-")),
    ("ihg", re.compile(r"ihg\.com/[a-z0-9]+/hotels/us/en/[^/]+/([a-z0-9]{5,7})/")),
    ("choice", re.compile(r"choicehotels\.com/.*?/([a-z]{2}\d{3})")),
    ("hyatt", re.compile(r"hyatt\.com/.*?/([a-z0-9]{5,6})-")),
)


def property_codes(url: object) -> frozenset:
    """Brand-scoped property codes a URL names.

    Brand-scoped because the namespaces collide: Marriott's SpringHill North
    Shore and IHG's Holiday Inn Express North Shore are both ``pitns``.
    """
    text = str(url or "").lower()
    out = set()
    for family, pattern in _CODE_PATTERNS:
        found = pattern.search(text)
        if found:
            out.add("%s:%s" % (family, found.group(1)))
    return frozenset(out)


def canonical_url(url: object) -> str:
    text = str(url or "").strip().lower().split("?")[0].rstrip("/")
    return text


def digits(value: object) -> str:
    only = re.sub(r"\D", "", str(value or ""))
    return only if len(only) == 10 else ""


def street(value: object) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(value or "").lower()).strip()


class Registry:
    """The registered 96, indexed by every signal that can PROVE an identity."""

    def __init__(self, hotels):
        self.by_key = {h["identity_key"]: h for h in hotels}
        self.by_url, self.by_code, self.by_addr, self.by_phone = {}, {}, {}, {}
        for h in hotels:
            for field in ("official_url", "policy_url", "website"):
                url = canonical_url(h.get(field))
                if url:
                    self.by_url.setdefault(url, h)
                for code in property_codes(h.get(field)):
                    self.by_code.setdefault(code, h)
            addr, phone = street(h.get("address")), digits(h.get("phone"))
            if addr:
                self.by_addr.setdefault(addr, h)
            if phone:
                self.by_phone.setdefault(phone, h)

    def resolve(self, signed: Mapping, shadow: Optional[Mapping]
                ) -> Tuple[Optional[str], str]:
        """``(registered identity_key, basis)`` -- or ``(None, 'UNBINDABLE')``."""
        key = signed["identity_key"]
        if key in self.by_key:
            return key, "DIRECT"

        url = canonical_url(signed.get("bound_source_url"))
        if url and url in self.by_url:
            return self.by_url[url]["identity_key"], "OFFICIAL_URL"

        codes = property_codes(signed.get("bound_source_url"))
        if shadow:
            codes = codes | property_codes(shadow.get("official_url"))
        for code in sorted(codes):
            if code in self.by_code:
                return self.by_code[code]["identity_key"], "PROPERTY_CODE"

        if shadow:
            addr, phone = street(shadow.get("address")), digits(shadow.get("phone"))
            if addr and phone:
                hit = self.by_addr.get(addr)
                if hit is not None and digits(hit.get("phone")) == phone:
                    return hit["identity_key"], "ADDRESS+PHONE"
            # A degraded census stub: same postal, same brand, and the
            # registered name is a strict prefix of the name discovery later
            # read off the property's own page.
            postal = str(shadow.get("postal_code") or "").strip()
            name = str(shadow.get("canonical_name") or "").lower()
            if postal and name:
                for other in self.by_key.values():
                    other_name = str(other.get("canonical_name") or "").lower()
                    if (str(other.get("postal_code") or "").strip() == postal
                            and other_name and other_name != name
                            and name.startswith(other_name)):
                        return other["identity_key"], "POSTAL+BRAND+NAME_PREFIX"
        return None, "UNBINDABLE"


# --------------------------------------------------------------------------- #
# The signed set.
# --------------------------------------------------------------------------- #

def signed_decisions() -> "OrderedDict[str, Dict]":
    """The 32 distinct signatures, in the order the founder gave them."""
    out: "OrderedDict[str, Dict]" = OrderedDict()
    for path, work_order in DECISIONS:
        ledger = _load(path)
        for row in ledger["signed"]:
            key = row["identity_key"]
            if key in out:
                raise SyncError("%s is signed twice (%s and %s); a decision may "
                                "be applied at most once"
                                % (key, out[key]["signed_by_work_order"], work_order))
            row = OrderedDict(row)
            row["signed_by_work_order"] = work_order
            out[key] = row
    return out


def holds() -> Tuple[str, ...]:
    return tuple(r["identity_key"] for r in _load(DECISIONS[-1][0])["withheld"])


def assert_founder_supersessions(rulings: Mapping) -> None:
    """The two retirements are the FOUNDER's, and must still read that way."""
    rows = {r["identity_key"]: r for r in rulings["rows"]}
    for winner, loser in FOUNDER_SUPERSESSIONS.items():
        keeps, drops = rows.get(winner), rows.get(loser)
        if not keeps or not drops:
            raise SyncError("supersession %r -> %r is not in the ruling ledger"
                            % (winner, loser))
        if keeps.get("founder_ruling") != "DUPLICATE_PRESERVED_QUALIFIED_IDENTITY":
            raise SyncError("%s is no longer the preserved identity" % winner)
        if drops.get("founder_ruling") != "RETIRED_STALE_TWIN":
            raise SyncError("%s is no longer a retired stale twin" % loser)
        if loser not in (keeps.get("founder_ruling_note") or ""):
            raise SyncError("the founder's note on %s no longer names %s"
                            % (winner, loser))


# --------------------------------------------------------------------------- #
# Phase 7.
# --------------------------------------------------------------------------- #

def reconcile() -> Dict:
    census = _load(CENSUS)
    if len(census["hotels"]) != 96:
        raise SyncError("the registered census is %d rows, not the registered 96 "
                        "-- the shadow 115 must not be promoted in this order"
                        % len(census["hotels"]))
    shadow = {h["identity_key"]: h for h in _load(RECENSUS)["hotels"]}
    registry = Registry(census["hotels"])
    rulings = _load(RULINGS)
    assert_founder_supersessions(rulings)

    signed = signed_decisions()
    held = holds()
    rows, targets = [], {}
    for key, row in signed.items():
        target, basis = registry.resolve(row, shadow.get(key))
        if target is not None and target in targets:
            raise SyncError("two signed rows (%s, %s) reconcile onto one "
                            "registered identity %r; that would create "
                            "duplicate authority"
                            % (targets[target], key, target))
        if target is not None:
            targets[target] = key
        retires = FOUNDER_SUPERSESSIONS.get(key)
        rows.append(OrderedDict((
            ("signed_identity_key", key),
            ("registered_identity_key", target),
            ("basis", basis),
            ("proposes_authority", row["proposes_authority"]),
            ("signed_by_work_order", row["signed_by_work_order"]),
            ("bound_source_url", row.get("bound_source_url")),
            ("bound_snapshot_hash", row.get("bound_snapshot_hash")),
            ("retires_stale_twin", retires),
        )))
    return OrderedDict((
        ("schema", "ptf-market-identity-reconciliation/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("what_this_is",
         "Each founder-signed disposition mapped onto the identity the "
         "REGISTERED 96-row census holds, by evidence a duplicate street "
         "identity cannot see. The shadow 115-row recensus is NOT promoted."),
        ("registered_census", len(census["hotels"])),
        ("shadow_recensus", len(shadow)),
        ("signed_total", len(signed)),
        ("bound", sum(1 for r in rows if r["registered_identity_key"])),
        ("unbindable", sum(1 for r in rows if not r["registered_identity_key"])),
        ("unbindable_are_census_adds",
         "Their property codes, addresses and phones collide with nothing in "
         "the registered 96, so each is an identity this market does not have. "
         "Applying one would ADD a census row, which this order reserves for a "
         "separate SUPERSEDE / ADD-NEVER-DOWNGRADE work order."),
        ("holds_untouched", list(held)),
        ("rows", rows),
    ))


# --------------------------------------------------------------------------- #
# Phase 8 -- build what the signatures authorise.
# --------------------------------------------------------------------------- #

def _observations() -> Dict[str, Dict]:
    return {r["identity_key"]: r for r in _load(OBSERVATIONS)["records"]}


def _artifact_sha(value: object) -> str:
    text = str(value or "").replace("-", "")
    return text if text.startswith("sha256:") else "sha256:%s" % text


def _evidence(observation: Mapping, fields: Tuple[str, ...]) -> List[Dict]:
    """The record's evidence array, from the observation's own bound entries.

    Only entries whose field is actually PUBLISHED are carried: the approval's
    ``evidence_hash`` is taken over this array, so a quote backing a fact the
    projection withheld would bind the founder to a fact the record never states.
    """
    out: List[Dict] = []
    seen = set()
    for entry in observation["publication_grade"]["evidence_entries"]:
        field = entry.get("field")
        if field not in fields:
            continue
        built = OrderedDict((
            ("field", field),
            ("quote", entry["quote"]),
            ("source_url", entry["source_url"]),
            ("artifact_class", entry["artifact_class"]),
            ("artifact_sha256", _artifact_sha(entry["artifact_sha256"])),
            ("artifact_kind", entry["artifact_kind"]),
            ("captured_at", entry["captured_at"]),
            ("capture_method", entry["capture_method"]),
            ("source_grade", entry["source_grade"]),
        ))
        built["evidence_ref"] = PM.evidence_ref_for(built)
        if built["evidence_ref"] in seen:
            continue
        seen.add(built["evidence_ref"])
        out.append(built)
    return out


def _caveats(signed: Mapping, row: Mapping, notes) -> List[str]:
    caveats = [
        "FOUNDER DECISION (%s): %s. Signed by %s on %s under %s, against the "
        "bound page %s."
        % (signed["reviewed_disposition"], signed["founder_decision"],
           signed.get("founder_reviewer_id") or REVIEWER,
           signed.get("founder_reviewed_at"), signed["signed_by_work_order"],
           signed.get("bound_snapshot_hash")),
        "%s applied this already-signed decision to the REGISTERED census "
        "identity %r on %s. The 115-row shadow recensus was not promoted, the "
        "signature is not re-asked, and its evidence is unchanged."
        % (WORK_ORDER, row["registered_identity_key"], row["basis"]),
        "Zero-cost sync: provider calls 0, spend $0.00. The evidence is the "
        "page this market already owned from PTF-PITTSBURGH-PAID-ACQUISITION-"
        "AUTHORIZATION-003, read offline.",
    ]
    if row.get("retires_stale_twin"):
        caveats.append(
            "SUPERSEDES: the founder ruled this the preserved qualified "
            "identity and retired the stale twin %r (RETIRED_STALE_TWIN, "
            "pittsburgh_pa_founder_rulings_003). The twin publishes nothing."
            % row["retires_stale_twin"])
    for note in notes:
        caveats.append("PROJECTION: %s" % note)
    return caveats


def build_record(row: Mapping, signed: Mapping, observation: Mapping,
                 census_row: Mapping, corrected: Mapping) -> Dict:
    key = row["registered_identity_key"]
    source = observation["observation"]
    # weight_comparison_from_source reads the comparison from the PROPERTY'S OWN
    # WORDING ("maximum weight of 50.0 lbs", "Max weight 40 lbs", "up to 30.0
    # lbs") and WITHHOLDS where it cannot read one. It is on because the schema
    # requires operator and scope whenever a weight publishes, and the reader
    # emits a value only; the alternative is a guest-visible error in both
    # directions. It matches what Pittsburgh's 37 committed records already
    # publish for the same wording.
    #
    # normalize_weight stays OFF. That switch is PTF-ST-LOUIS-PUBLICATION-
    # SCHEMA-DECISIONS-010 -- ANOTHER market's founder decision, which would
    # flatten an unqualified ceiling this market's founder never ruled on.
    facts, notes = project_facts(source["extraction"], source.get("evidence") or (),
                                 weight_comparison_from_source=True)
    if facts.get("pets_allowed") is not True:
        raise SyncError("%s: the observation does not state pets_allowed=true" % key)
    entries = _evidence(observation, tuple(facts) + ("pets_allowed",))
    if not entries:
        raise SyncError("%s: no publication-grade evidence backs a published field"
                        % key)
    name = corrected.get(signed["identity_key"]) or census_row["canonical_name"]
    record = OrderedDict((
        ("key", key),
        ("name", name),
        ("facts", facts),
        ("evidence", entries),
        ("evidence_count", len(entries)),
        ("evidence_quote", " [.] ".join(e["quote"].strip() for e in entries)),
        ("source_url", source["source_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", source["observed_at"]),
        ("verified_at", source["observed_at"]),
        ("worker_model_id", ""),
        ("worker_prompt_version", ""),
        ("worker_result_hash", str(source.get("snapshot_hash") or "").replace("-", "")),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("identity_key", key),
        ("market_id", MARKET_ID),
    ))
    record["computation_class"] = classify(facts).computation_class
    record["approval"] = OrderedDict((
        ("decision", signed["founder_decision"]),
        ("operator", OPERATOR),
        ("approval_date", signed.get("founder_reviewed_at") or AS_OF),
        ("caveats", _caveats(signed, row, notes)),
        ("record_hash", PM.record_hash(
            {k: v for k, v in record.items() if k != "approval"})),
        ("evidence_hash", PM.evidence_hash(entries)),
    ))
    return record


def build_exclusion(row: Mapping, signed: Mapping, observation: Mapping,
                    census_row: Mapping, corrected: Mapping) -> Dict:
    key = row["registered_identity_key"]
    source = observation["observation"]
    if source["extraction"].get("pets_allowed") is not False:
        raise SyncError("%s: the observation does not state pets_allowed=false" % key)
    entries = _evidence(observation, ("pets_allowed",))
    if not entries:
        raise SyncError("%s: a refusal needs the sentence that refuses" % key)
    # An exclusion's canonical_name MUST be the one its normalized_name derives
    # from -- hotel_exclusions.validate refuses otherwise. So the CENSUS name is
    # used here even when the name-correction overlay has a better one: that
    # overlay is explicitly a display layer ("the census is not edited: it
    # remains the record of what discovery OBSERVED, and this overlay is what a
    # reader should be shown instead"), and a reader still gets the corrected
    # name from the overlay at render time. Taking the corrected name here
    # instead would make "comfort suites" fail to derive from "Comfort Suites
    # Monroeville - Pittsburgh East".
    name = census_row["canonical_name"]
    display = corrected.get(signed["identity_key"])
    for field in ("address", "city", "state", "postal_code"):
        if not str(census_row.get(field) or "").strip():
            raise SyncError("%s: the census row has no %s, and an exclusion "
                            "record requires one" % (key, field))
    record = OrderedDict((
        ("exclusion_id", "pgh-%s" % key.replace(" ", "-")),
        ("canonical_name", name),
        ("normalized_name", key),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("official_url", source["source_url"]),
        ("exclusion_state", HE.VERIFIED_NO_PETS),
        ("evidence_quote", entries[0]["quote"]),
        ("source_url", source["source_url"]),
        ("observed_at", source["observed_at"]),
        ("source_hash", _artifact_sha(source.get("snapshot_hash"))),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", signed.get("founder_reviewed_at") or AS_OF),
        ("notes", " ".join(_caveats(signed, row, ()) + (
            ["DISPLAY NAME: the name-correction overlay shows this property as "
             "%r; the census name is kept here because normalized_name must "
             "derive from it." % display] if display else []))),
        ("market_id", MARKET_ID),
    ))
    record["record_hash"] = HE.record_hash(record)
    record["approval_hash"] = HE.approval_hash(record)
    return record


def apply_signed():
    reconciliation = reconcile()
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    corrected = corrected_names(_load(OVERLAY) if OVERLAY.is_file() else None)
    obs = _observations()
    signed_rows = signed_decisions()
    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"]}

    records, exclusions, applied, already, unbindable = [], [], [], [], []
    for row in reconciliation["rows"]:
        key = row["registered_identity_key"]
        signed_key = row["signed_identity_key"]
        if key is None:
            unbindable.append(row)
            continue
        signed = signed_rows[signed_key]
        wants_publish = row["proposes_authority"] == PUBLISH
        if (wants_publish and key in published) or (
                not wants_publish and key in excluded):
            already.append(row)
            continue
        if key in published or key in excluded:
            raise SyncError("%s already holds the OTHER authority; a signed "
                            "decision may not silently reverse one" % key)
        observation = obs.get(signed_key)
        if observation is None:
            raise SyncError("%s has no observation to publish from" % signed_key)
        if observation["publication_grade"]["verdict"] != "PUBLICATION_GRADE_CONFIRMED":
            raise SyncError("%s is not publication grade" % signed_key)
        census_row = census[key]
        if wants_publish:
            records.append(build_record(row, signed, observation, census_row,
                                        corrected))
        else:
            exclusions.append(build_exclusion(row, signed, observation,
                                              census_row, corrected))
        applied.append(row)

    keys = [r["identity_key"] for r in records]
    ex_keys = [e["normalized_name"] for e in exclusions]
    if len(set(keys)) != len(keys) or len(set(ex_keys)) != len(ex_keys):
        raise SyncError("this order would write one identity twice")
    if set(keys) & set(ex_keys):
        raise SyncError("an identity would be published AND excluded: %s"
                        % sorted(set(keys) & set(ex_keys)))
    if (set(keys) & published) or (set(ex_keys) & excluded):
        raise SyncError("this order would re-apply an existing decision")
    # A HOLD is a disposition on a SIGNED CANDIDATE (a recensus identity), not
    # on the registered identity a signature is applied to. The two namespaces
    # collide by name exactly where the founder ruled a supersession: the
    # recensus row "courtyard by marriott pittsburgh university center" is the
    # RETIRED stale twin, while the REGISTERED row of that name is the building
    # its qualified successor publishes. So this compares signed keys.
    applied_signed = {r["signed_identity_key"] for r in applied}
    for held in holds():
        if held in applied_signed:
            raise SyncError("held signed candidate %r would be applied" % held)

    package["hotels"] = list(package["hotels"]) + records
    problems = PM.validate_migrated(package)
    if problems:
        raise SyncError("the package does not validate: %s" % problems[:6])
    shard["exclusions"] = list(shard["exclusions"]) + exclusions
    shard["count"] = len(shard["exclusions"])
    HE.validate(shard)

    def summarise(row, outcome):
        return OrderedDict((
            ("signed_identity_key", row["signed_identity_key"]),
            ("registered_identity_key", row["registered_identity_key"]),
            ("basis", row["basis"]),
            ("proposes_authority", row["proposes_authority"]),
            ("signed_by_work_order", row["signed_by_work_order"]),
            ("outcome", outcome),
            ("retires_stale_twin", row.get("retires_stale_twin")),
        ))

    report = OrderedDict((
        ("schema", "ptf-market-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("parent_work_orders", [w for _p, w in DECISIONS]),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("operator", OPERATOR),
        ("note",
         "The 32 already-signed Pittsburgh founder decisions applied to the "
         "REGISTERED 96-identity census. No signature was re-asked, no "
         "disposition re-derived, and the 115-row shadow recensus was not "
         "promoted. Provider calls 0, spend $0.00."),
        ("signed_total", reconciliation["signed_total"]),
        ("applied", len(applied)),
        ("already_satisfied_by_existing_authority", len(already)),
        ("unbindable_needs_census_add", len(unbindable)),
        ("net_new_pet_friendly", len(records)),
        ("net_new_verified_no_pets", len(exclusions)),
        ("holds_remaining", list(holds())),
        ("rows", ([summarise(r, "APPLIED") for r in applied]
                  + [summarise(r, "ALREADY_IN_AUTHORITY") for r in already]
                  + [summarise(r, "NOT_APPLIED_REQUIRES_CENSUS_ADD")
                     for r in unbindable])),
    ))
    return package, records, exclusions, report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        reconciliation = reconcile()
        package, records, exclusions, report = apply_signed()
    except SyncError as exc:
        print("REFUSED: %s" % exc)
        return 2
    print("registered census : %d" % reconciliation["registered_census"])
    print("shadow recensus   : %d (NOT promoted)" % reconciliation["shadow_recensus"])
    print("signed decisions  : %d" % report["signed_total"])
    print("  applied         : %d" % report["applied"])
    print("  already held    : %d" % report["already_satisfied_by_existing_authority"])
    print("  needs census add: %d" % report["unbindable_needs_census_add"])
    print("net-new PF        : %d" % report["net_new_pet_friendly"])
    print("net-new no-pets   : %d" % report["net_new_verified_no_pets"])
    print("holds remaining   : %d" % len(report["holds_remaining"]))
    print("package records   : %d" % len(package["hotels"]))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    REPORTS.mkdir(parents=True, exist_ok=True)
    _write(RECONCILIATION, reconciliation)
    print("WROTE %s" % RECONCILIATION.name)
    _write(PACKAGE, package)
    print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))
    shard = MA.load_market_exclusions_document(MARKET_ID)
    shard["exclusions"] = list(shard["exclusions"]) + exclusions
    shard["count"] = len(shard["exclusions"])
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE exclusions shard (%d rows)" % shard["count"])
    _write(APPLICATION, report)
    print("WROTE %s" % APPLICATION.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
