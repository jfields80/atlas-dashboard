"""PTF-DISCOVERY-P0-001 -- the Florida DBPR public-lodging REGISTRY adapter.

Parses the Florida Department of Business and Professional Regulation's
active public-lodging license extract (the ``hrlodge<district>.csv`` files
published on the DBPR "Lodging - Public Records" page) into
``ptf-identity-observation/1.0`` records. First member of the REGISTRY
source family, and the template for every future registry adapter.

TERMS (re-verified 2026-08-07 against the authoritative source, per FD-R5):
the extracts are published unauthenticated on the official state page
https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/
under the heading "Public Records"; the site disclaimer
(https://www2.myfloridalicense.com/disclaimer/) states no restriction on
use of the downloaded data. Florida public-lodging license records are
public records. Retrieval is a bulk-file download -- no crawl, no API key,
no per-record request.

BOUNDS (the adapter's entire job, per the work order):

* Text in, observations out. NO network access here -- the caller supplies
  already-downloaded CSV text plus its provenance (URL, retrieval time,
  snapshot hash). Pure and deterministic.
* Emits ``ptf-identity-observation/1.0`` ONLY. No market data, no census
  writes, no identity resolution, no policy anything.
* Passes every row through rather than deciding the lodging boundary:
  which DBPR license classes count as transient lodging is a founder
  decision (FD-R8), so a row outside the hotel/motel rank codes is emitted
  WITH a ``W_AMBIGUOUS_ROW`` warning, never silently dropped or silently
  included as settled.
* A row too broken to observe (no name, or no license number) is returned
  in the ``skipped`` list with its reason -- never a partial silent batch.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery.identity_observation import (  # noqa: E402
    CONTRACT_VERSION,
    validate_emission_batch,
)
from scripts.pettripfinder.discovery.property_identity import (  # noqa: E402
    normalize_phone,
)
from scripts.pettripfinder.discovery.source_families import (  # noqa: E402
    FAMILY_REGISTRY,
)

SOURCE_ID = "fl_dbpr_lodging"
SOURCE_FAMILY = FAMILY_REGISTRY
PROPERTY_CODE_NAMESPACE = "FL_DBPR"

#: Column headers exactly as DBPR publishes them (hrlodge extract layout,
#: verified against the live District 1 file on 2026-08-07). Only the
#: columns named here are ever read; an extra column -- whatever it is
#: called -- is structurally ignored, so a hypothetical policy-named column
#: could never reach an observation.
COL_LICENSEE_NAME = "Licensee Name"
COL_RANK_CODE = "Rank Code"
COL_BUSINESS_NAME = "Business Name"
COL_LOCATION_ADDRESS = "Location Street Address"
COL_LOCATION_ADDRESS_2 = "Location Address Line 2"
COL_LOCATION_CITY = "Location City"
COL_LOCATION_STATE = "Location State Code"
COL_LOCATION_ZIP = "Location Zip Code"
COL_PRIMARY_PHONE = "Primary Phone Number"
COL_SECONDARY_PHONE = "Secondary Phone Number"
COL_LICENSE_NUMBER = "License Number"

REQUIRED_COLUMNS = (
    COL_LICENSEE_NAME, COL_RANK_CODE, COL_BUSINESS_NAME, COL_LOCATION_ADDRESS,
    COL_LOCATION_CITY, COL_LOCATION_STATE, COL_LOCATION_ZIP,
    COL_LICENSE_NUMBER,
)

#: DBPR rank codes whose lodging character is settled vocabulary (hotel and
#: motel). Every OTHER rank code (vacation-rental condo/dwelling classes,
#: apartment classes, ...) straddles the FD-R8 license-class boundary and is
#: emitted with W_AMBIGUOUS_ROW for downstream adjudication.
UNAMBIGUOUS_LODGING_RANK_CODES = frozenset({"HOTL", "MOTL"})


class DbprAdapterError(ValueError):
    """The supplied text is not a DBPR hrlodge extract (fail closed)."""


def _clean(value: str) -> str:
    return " ".join((value or "").split())


def _five_digit_zip(raw: str) -> Tuple[str, bool]:
    """DBPR writes ZIPs as '33139', '331394209' or '33139-5808'; the first
    five digits are the ZIP, the rest is the +4. (clean_zip, ok)."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if len(digits) in (5, 9):
        return digits[:5], True
    return "", False


def parse_hrlodge_csv(csv_text: str, *,
                      observed_at: str,
                      retrieved_at: str,
                      raw_pointer_prefix: str,
                      snapshot_hash: str = "",
                      license_tag: str = "") -> Tuple[List[Dict], List[Dict]]:
    """(observations, skipped) for one DBPR active-lodging extract.

    ``raw_pointer_prefix`` names the file the caller downloaded (URL or
    path); each observation's ``raw_pointer`` appends ``#row=<n>`` where
    ``<n>`` is the 1-based data-row number, so any assertion can be
    re-found in the raw snapshot. ``observed_at`` is the date the extract
    asserts its contents (the extract's publication date), never the
    retrieval date. The returned batch has already passed
    ``validate_emission_batch`` -- the same check the ingestion boundary
    runs -- so a defective adapter fails here, in its own tests.
    """
    reader = csv.DictReader(io.StringIO(csv_text or ""))
    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise DbprAdapterError(
            "not a DBPR hrlodge extract: missing column(s) %s (got %s)"
            % (missing, header[:6]))

    observations: List[Dict] = []
    skipped: List[Dict] = []
    for row_number, row in enumerate(reader, start=1):
        raw_pointer = "%s#row=%d" % (raw_pointer_prefix, row_number)
        warnings: List[Dict] = []

        license_number = _clean(row.get(COL_LICENSE_NUMBER, ""))
        business_name = _clean(row.get(COL_BUSINESS_NAME, ""))
        licensee_name = _clean(row.get(COL_LICENSEE_NAME, ""))
        name = business_name or licensee_name
        if not license_number or not name:
            skipped.append({
                "raw_pointer": raw_pointer,
                "reason": "no license number" if not license_number
                          else "no business or licensee name",
            })
            continue
        if not business_name:
            warnings.append({
                "code": "W_AMBIGUOUS_ROW",
                "detail": "no Business Name; using Licensee Name %r, which may "
                          "be a corporate entity rather than the property's "
                          "operating name" % licensee_name})

        rank_code = _clean(row.get(COL_RANK_CODE, ""))
        if rank_code and rank_code not in UNAMBIGUOUS_LODGING_RANK_CODES:
            warnings.append({
                "code": "W_AMBIGUOUS_ROW",
                "detail": "rank code %r straddles the FD-R8 lodging boundary; "
                          "passed through for downstream adjudication" % rank_code})

        address = _clean(row.get(COL_LOCATION_ADDRESS, ""))
        address_2 = _clean(row.get(COL_LOCATION_ADDRESS_2, ""))
        if address_2:
            address = _clean("%s %s" % (address, address_2))
        if not address:
            warnings.append({
                "code": "W_ADDR_UNPARSED",
                "detail": "no location street address in the extract row"})

        zip_clean, zip_ok = _five_digit_zip(row.get(COL_LOCATION_ZIP, ""))
        if not zip_ok and _clean(row.get(COL_LOCATION_ZIP, "")):
            warnings.append({
                "code": "W_ADDR_UNPARSED",
                "detail": "unparseable ZIP %r; field dropped"
                          % _clean(row.get(COL_LOCATION_ZIP, ""))})

        # The location's own line is the secondary column in this extract;
        # the primary is the licensee/mailing contact. Prefer the location.
        phone = ""
        for raw_phone in (_clean(row.get(COL_SECONDARY_PHONE, "")),
                          _clean(row.get(COL_PRIMARY_PHONE, ""))):
            if not raw_phone:
                continue
            if normalize_phone(raw_phone):
                phone = raw_phone
                break
            warnings.append({
                "code": "W_PHONE_INVALID",
                "detail": "phone column contained %r (not a 10-digit US "
                          "number); field dropped" % raw_phone})

        observation = {
            "obs_id": "fl-dbpr-%06d" % row_number,
            "contract_version": CONTRACT_VERSION,
            "source_id": SOURCE_ID,
            "source_family": SOURCE_FAMILY,
            "observed_at": observed_at,
            "name": name,
            "parse_confidence": "HIGH" if not warnings else "MEDIUM",
            "warnings": warnings,
            "property_code": "%s:%s" % (PROPERTY_CODE_NAMESPACE, license_number),
            "provenance": {
                "retrieval_mode": "bulk_file",
                "retrieved_at": retrieved_at,
                "raw_pointer": raw_pointer,
                "ephemeral": False,
            },
        }
        if snapshot_hash:
            observation["provenance"]["snapshot_hash"] = snapshot_hash
        if license_tag:
            observation["provenance"]["license_tag"] = license_tag
        if address:
            observation["address"] = address
        city = _clean(row.get(COL_LOCATION_CITY, ""))
        if city:
            observation["city"] = city
        state = _clean(row.get(COL_LOCATION_STATE, ""))
        if state:
            observation["state"] = state
        if zip_clean:
            observation["zip"] = zip_clean
        if phone:
            observation["phone"] = phone
        if rank_code:
            observation["category_hint"] = rank_code
            observation["license_class"] = rank_code
        observations.append(observation)

    return validate_emission_batch(observations), skipped


def build_adapter_manifest() -> Dict:
    """The adapter's self-declaration (adapter_manifest.schema.json shape)."""
    return {
        "source_id": SOURCE_ID,
        "source_family": SOURCE_FAMILY,
        "contract_version": CONTRACT_VERSION,
        "retrieval_mode": "bulk_file",
        "licensing_note": (
            "VERIFIED 2026-08-07: Florida DBPR publishes active public-lodging "
            "license extracts as unauthenticated CSV downloads on the official "
            "'Lodging - Public Records' page "
            "(https://www2.myfloridalicense.com/hotels-restaurants/"
            "lodging-public-records/); the site disclaimer states no "
            "restriction on use of the downloaded data."),
        "storable": True,
        "freshness_cadence": "monthly",
        "upstream_provenance": [],
    }


__all__ = [
    "SOURCE_ID", "SOURCE_FAMILY", "PROPERTY_CODE_NAMESPACE",
    "UNAMBIGUOUS_LODGING_RANK_CODES", "REQUIRED_COLUMNS",
    "DbprAdapterError", "parse_hrlodge_csv", "build_adapter_manifest",
]
