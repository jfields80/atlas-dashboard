"""AES-DATA-001 importer -- deterministic structured-metadata extraction
(mission section 7). Reads JSON-LD (schema.org Hotel/Restaurant/Park/
LodgingBusiness/FoodEstablishment/LocalBusiness), microdata, Open Graph,
meta, canonical, tel: links, and PostalAddress blocks. Pure and
deterministic; never trusts metadata blindly -- conflicts with visible text
are surfaced downstream, not silently resolved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.normalize import normalize_whitespace

_BUSINESS_TYPES = frozenset({
    "hotel", "lodgingbusiness", "resort", "motel", "bedandbreakfast",
    "restaurant", "foodestablishment", "barorpub", "brewery", "cafeorcoffeeshop",
    "park", "touristattraction", "civicstructure", "localbusiness", "place",
    # AES-DATA-003B: veterinary business-node recognition only -- this list
    # only decides which JSON-LD node is read for name/address/phone/website
    # (Task 13). It has no path to emergency_service, urgent_care, open_24h,
    # walk_ins_accepted, existing_clients_only, or species/exotic capability
    # facts; this module never emits those field names (see the
    # StructuredField construction sites above), so recognizing these types
    # cannot establish a high-risk capability by itself.
    "veterinarycare", "medicalbusiness",
})


@dataclass(frozen=True)
class StructuredField:
    field_name: str
    value: str
    quote: str
    method: str


@dataclass(frozen=True)
class StructuredExtraction:
    fields: Tuple[StructuredField, ...] = ()
    entity_names: Tuple[str, ...] = ()
    multi_entity: bool = False

    def by_field(self) -> Dict[str, StructuredField]:
        # First occurrence wins (JSON-LD before OG before meta by insertion).
        out: Dict[str, StructuredField] = {}
        for f in self.fields:
            out.setdefault(f.field_name, f)
        return out


def _type_tokens(node: dict) -> List[str]:
    t = node.get("@type", "")
    vals = t if isinstance(t, list) else [t]
    return [str(v).strip().lower() for v in vals if v]


def _walk_jsonld(obj, businesses: List[dict]) -> None:
    if isinstance(obj, dict):
        if any(tok in _BUSINESS_TYPES for tok in _type_tokens(obj)):
            businesses.append(obj)
        for key in ("@graph", "itemListElement", "mainEntity"):
            if key in obj:
                _walk_jsonld(obj[key], businesses)
    elif isinstance(obj, list):
        for item in obj:
            _walk_jsonld(item, businesses)


def _address_from_jsonld(node: dict) -> Dict[str, str]:
    addr = node.get("address")
    out: Dict[str, str] = {}
    if isinstance(addr, list):
        addr = addr[0] if addr else None
    if isinstance(addr, dict):
        out["address"] = normalize_whitespace(str(addr.get("streetAddress", "")))
        out["city"] = normalize_whitespace(str(addr.get("addressLocality", "")))
        out["state"] = normalize_whitespace(str(addr.get("addressRegion", "")))
        out["postal_code"] = normalize_whitespace(str(addr.get("postalCode", "")))
    elif isinstance(addr, str):
        out["address"] = normalize_whitespace(addr)
    return {k: v for k, v in out.items() if v}


def _extract_jsonld(soup: BeautifulSoup) -> Tuple[List[StructuredField], List[str]]:
    fields: List[StructuredField] = []
    names: List[str] = []
    businesses: List[dict] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue                      # malformed JSON-LD is skipped, not fatal
        _walk_jsonld(data, businesses)
    for node in businesses:
        name = normalize_whitespace(str(node.get("name", "")))
        if name:
            names.append(name)
    if not businesses:
        return (fields, names)
    primary = businesses[0]
    name = normalize_whitespace(str(primary.get("name", "")))
    if name:
        fields.append(StructuredField("name", name, name, C.METHOD_JSON_LD))
    tel = normalize_whitespace(str(primary.get("telephone", "")))
    if tel:
        fields.append(StructuredField("phone", tel, tel, C.METHOD_JSON_LD))
    for k, v in _address_from_jsonld(primary).items():
        method = C.METHOD_ADDRESS_BLOCK if k != "name" else C.METHOD_JSON_LD
        fields.append(StructuredField(k, v, v, method))
    url = normalize_whitespace(str(primary.get("url", "")))
    if url:
        fields.append(StructuredField("website_url", url, url, C.METHOD_JSON_LD))
    return (fields, names)


def _extract_opengraph(soup: BeautifulSoup) -> List[StructuredField]:
    fields: List[StructuredField] = []
    title = soup.find("meta", attrs={"property": "og:title"})
    if title and title.get("content"):
        v = normalize_whitespace(title["content"])
        fields.append(StructuredField("name", v, v, C.METHOD_OPEN_GRAPH))
    url = soup.find("meta", attrs={"property": "og:url"})
    if url and url.get("content"):
        v = normalize_whitespace(url["content"])
        fields.append(StructuredField("website_url", v, v, C.METHOD_OPEN_GRAPH))
    return fields


def _extract_tel(soup: BeautifulSoup) -> List[StructuredField]:
    a = soup.select_one("a[href^='tel:']")
    if a and a.get("href"):
        raw = a["href"].split(":", 1)[1]
        return [StructuredField("phone", raw, normalize_whitespace(a.get_text() or raw),
                                C.METHOD_TEL_LINK)]
    return []


def _extract_microdata_address(soup: BeautifulSoup) -> List[StructuredField]:
    fields: List[StructuredField] = []
    block = soup.select_one("[itemtype*='PostalAddress']")
    if not block:
        return fields
    mapping = {
        "streetAddress": "address", "addressLocality": "city",
        "addressRegion": "state", "postalCode": "postal_code",
    }
    for prop, fieldname in mapping.items():
        el = block.select_one("[itemprop='%s']" % prop)
        if el:
            v = normalize_whitespace(el.get("content") or el.get_text() or "")
            if v:
                fields.append(StructuredField(fieldname, v, v, C.METHOD_MICRODATA))
    return fields


def extract_structured_metadata(html: str) -> StructuredExtraction:
    """Deterministic structured extraction. First source wins per field
    (JSON-LD, then microdata, then OG, then tel)."""
    soup = BeautifulSoup(html, "html.parser")
    all_fields: List[StructuredField] = []
    jsonld_fields, names = _extract_jsonld(soup)
    all_fields.extend(jsonld_fields)
    all_fields.extend(_extract_microdata_address(soup))
    all_fields.extend(_extract_opengraph(soup))
    all_fields.extend(_extract_tel(soup))

    unique_names = tuple(dict.fromkeys(n for n in names if n))
    multi_entity = len(unique_names) > 1
    return StructuredExtraction(
        fields=tuple(all_fields),
        entity_names=unique_names,
        multi_entity=multi_entity,
    )
