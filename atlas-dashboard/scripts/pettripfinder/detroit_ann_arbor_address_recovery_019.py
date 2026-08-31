# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019 -- address repair.

Recovers the one street address a publication gate needed, from evidence this
project already owns. NO PROVIDER IS CALLED.

Sheraton Detroit Novi failed listing readiness because the census carries no
street for it -- the same class of blocker order 011 found and order 012
cleared. The fix is the same and is not a loosening of the gate: the property's
OWN rendered page, bought in order 015 and still persisted with its sha256,
states a PostalAddress. The gate then passes on the property's own evidence.

Only blanks are filled. A stated census value is never overwritten from a page,
because that would be a silent re-identification rather than a repair.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_surface as PS   # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key      # noqa: E402
from scripts.pettripfinder import (                                 # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019"
AS_OF = "2026-08-30"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PRECHECK = LP / "detroit_ann_arbor_brightdata_precheck_019.json"
OUT_PATH = LP / "detroit_ann_arbor_address_recovery_019.json"

if __name__ == "__main__":
    precheck = R11.load(PRECHECK)
    census = R11.load(CENSUS_PATH)
    by_key = {row["identity_key"]: row for row in census["hotels"]}

    results, applied = [], 0
    for row in precheck["rejected_rows"]:
        key = row["identity_key"]
        reading = row.get("reading") or {}
        path = _REPO_ROOT / (reading.get("document_artifact") or "")
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("gate_failures", row.get("gate_failures")),
            ("evidence", "the property's own PostalAddress JSON-LD in the "
                         "rendered page persisted by order %s"
                         % row["acquired_by_order"]),
            ("document_artifact", reading.get("document_artifact")),
            ("paid_again", False),
        ])
        if not path.is_file():
            entry["result"] = "WITHHELD"
            entry["why"] = "the source document is not on disk"
            results.append(entry)
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        recorded = reading.get("document_sha256") or ""
        if recorded and digest != recorded:
            entry["result"] = "WITHHELD"
            entry["why"] = "the document sha256 does not reproduce"
            results.append(entry)
            continue
        entry["document_sha256"] = digest
        node = PS.any_hotel_jsonld(raw.decode("utf-8", errors="replace")) or {}
        address = node.get("address") if isinstance(node.get("address"),
                                                    dict) else {}
        street = str(address.get("streetAddress") or "").strip()
        postal = str(address.get("postalCode") or "").strip()
        if not street or not postal:
            entry["result"] = "WITHHELD"
            entry["why"] = ("the document states no street address and postal "
                            "code; nothing is inferred")
            results.append(entry)
            continue
        crow = by_key.get(key)
        if crow is None:
            entry["result"] = "WITHHELD"
            entry["why"] = "no census row"
            results.append(entry)
            continue
        entry["result"] = "RECOVERED"
        entry["recovered"] = OrderedDict([
            ("street", street), ("postal_code", postal),
            ("locality", str(address.get("addressLocality") or "").strip()),
            ("stated_name", str(node.get("name") or "").strip()),
            ("telephone", str(node.get("telephone") or "").strip()),
        ])
        entry["census_before"] = OrderedDict([
            ("address", crow.get("address") or ""),
            ("postal_code", crow.get("postal_code") or "")])
        for field, value in (("address", street), ("postal_code", postal)):
            if str(crow.get(field) or "").strip():
                entry.setdefault("left_alone", []).append(field)
                continue
            crow[field] = value
        if not str(crow.get("phone") or "").strip() and entry["recovered"]["telephone"]:
            crow["phone"] = entry["recovered"]["telephone"]
        crow["street_identity"] = address_key(crow.get("address") or "",
                                              crow.get("postal_code") or "")
        entry["census_after"] = OrderedDict([
            ("address", crow.get("address") or ""),
            ("postal_code", crow.get("postal_code") or ""),
            ("street_identity", crow["street_identity"])])
        applied += 1
        results.append(entry)

    if applied:
        census["note"] = (
            "%s recovered %d street address(es) from the properties' own "
            "first-party PostalAddress JSON-LD, in pages this market had "
            "already paid for and persisted. No provider was called and no "
            "stated value was overwritten -- only blanks were filled. %s"
            % (WORK_ORDER, applied, census.get("note") or ""))
        R11.write_lf(CENSUS_PATH, census)

    R11.write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-address-recovery/1.1"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note", "A gate that refused for a missing fact is satisfied by "
                 "supplying the fact from first-party evidence, never by "
                 "relaxing the gate."),
        ("recovered", applied), ("withheld", len(results) - applied),
        ("results", results),
    ]))
    print("recovered %d of %d rejected rows at $0" % (applied, len(results)))
    for entry in results:
        print("   %-38s %s" % (entry["canonical_name"][:38], entry["result"]))
