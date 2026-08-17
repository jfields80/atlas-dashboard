"""Build Indianapolis Pass 2 capture-results and founder-review packets.

Pass-2 artifacts are unchanged. This builder re-scores those ten rows
against a STRICT identity gate before any policy observation is retained:

    PROPERTY URL ALONE IS NOT IDENTITY BINDING.
    If a page does not bind cleanly: IDENTITY_UNCERTAIN. Do not use its policy.

A retained policy row must show two independent non-URL keys (JSON-LD
street and JSON-LD phone) and a first-party property-specific policy
surface. A canonical-URL property code is recorded but never counted
as a bind. Founder decisions are not applied.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
CENSUS = LP / "identity_census" / "indianapolis-in.json"
WORK_ORDER = "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001"
GATE = "STRICT_TWO_INDEPENDENT_NON_URL_KEYS"

# Artifact hashes from the gitignored worker tree (re-derived).
ART = {
    "crowne plaza indianapolis downtown union station": {
        "file": "www-ihg-com-crowneplaza-hotels-us-en-indianapolis-inddt-hoteldetail-2026-08-16T23-34-26-159Z.json",
        "html": "sha256:04a917429e58067512df65a39b783edfdeb7115c9b9412c72d450d849bdb53b0",
        "text": "sha256:fe16dbf33d84a65cda4e2845cf4efc4b98308ad99a67a3fa2c27abf5f5a0053e",
        "png": "sha256:b28a4ae6080b7a61ee651bae112650a5b03dcb56324e5a2b9d8c14bef2331ff6",
        "bundle": "sha256:05751c62dd039478ff947a9e1e694a392905314a8e47c0720499ff546ba90ab0",
        "at": "2026-08-16T23:34:26.159Z",
        "url": "https://www.ihg.com/crowneplaza/hotels/us/en/indianapolis/inddt/hoteldetail",
    },
    "holiday inn express plainfield": {
        "file": "www-ihg-com-holidayinnexpress-hotels-us-en-plainfield-indsw-hoteldetail-2026-08-16T23-40-10-365Z.json",
        "html": "sha256:78724d7f36d53f35103bc99808ae47644ec9ebf7b715d8af65fc53878dad6e2d",
        "text": "sha256:db757296db075816c05083082c1af0698267e83195bfc59e33a8d6fa369313cc",
        "png": "sha256:82013404120bfb9bcaa16fa48b46b5bc55c4f11d338b0045de01ef2a0863cb31",
        "bundle": "sha256:f8484b20286538b6b143d0fc6e0fb965b8f258e5495f818cee472b778dad97ee",
        "at": "2026-08-16T23:40:10.365Z",
        "url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/plainfield/indsw/hoteldetail",
    },
    "courtyard by marriott indianapolis castleton": {
        "file": "www-marriott-com-en-us-hotels-indcs-courtyard-indianapolis-castleton-overview-2026-08-16T23-36-05-052Z.json",
        "html": "sha256:b11b710af01cdbb6d4784319f6a9dd31dacd66d0d25934c728b2b7fdc7d0ad36",
        "text": "sha256:2871aa5f74f475db3133c50346a8859625d8a0200b203a24440fe59907268392",
        "png": "sha256:3509147773a035d52ae24f6c02ee5cf0e4ca3ba0f6abaaf374753db658815f50",
        "bundle": "sha256:f2d929d7891c4bcc54f8d3be109b4d63c07fa44add351f2fc4ea181a2dfb908f",
        "at": "2026-08-16T23:36:05.052Z",
        "url": "https://www.marriott.com/en-us/hotels/indcs-courtyard-indianapolis-castleton/overview/",
    },
    "fairfield inn and suites indianapolis airport": {
        "file": "www-marriott-com-en-us-hotels-indfa-fairfield-inn-and-suites-indianapolis-airpor-2026-08-16T23-45-47-536Z.json",
        "html": "sha256:1a703848d019546e7ed5d1e74e0d5537e8f6c136a0c4995fc7f9252d2916ed27",
        "text": "sha256:604a256c06bd74c6fd120e13f498775ccb7fd6f3a0a83186816c14c298b82992",
        "png": "sha256:29acb8c85a9a86b9b6bae61ed169090e2711203533ffa503d508fb7b661350db",
        "bundle": "sha256:c33fc38e7116345a81dd0aea7663225ab07b2f3fc7c2bb2cccbda091c4291b6d",
        "at": "2026-08-16T23:45:47.536Z",
        "url": "https://www.marriott.com/en-us/hotels/indfa-fairfield-inn-and-suites-indianapolis-airport/overview/",
    },
    "jw marriott indianapolis": {
        "file": "www-marriott-com-en-us-hotels-indjw-jw-marriott-indianapolis-overview-2026-08-16T23-48-15-887Z.json",
        "html": "sha256:2eabcbe4f504d9ad50167262366df63e3198f76a41aa12f727b446ecc3272ba9",
        "text": "sha256:6d86ea285f2bb5cc3060030746f713dc966aad4e51047841dbc799cefee87a31",
        "png": "sha256:cd76cd865903e8dd88872ecc602e10630b4d3613f0daab690ce6a036a6f5f14e",
        "bundle": "sha256:bc9f681e4d12a32e6c19f1bb57a2de4fcc971dacea8e81d8508d9f5222baf3e4",
        "at": "2026-08-16T23:48:15.887Z",
        "url": "https://www.marriott.com/en-us/hotels/indjw-jw-marriott-indianapolis/overview/",
    },
    "le meridien indianapolis": {
        "file": "www-marriott-com-en-us-hotels-indmd-le-meridien-indianapolis-overview-2026-08-16T23-50-11-789Z.json",
        "html": "sha256:60dd50d47a9337aa7108e85765c8e79eb21ad165c07a7f1a044fe868530d3b28",
        "text": "sha256:5b9707a8ad4dccefa83d6fa72ca1003da296b85e4ac444a7a5784d1906f72824",
        "png": "sha256:949562524b6048763f6980b8759dfd27fe8bc658d43319dc9ed50d229ae9f09b",
        "bundle": "sha256:5b5baa74d4fd555eb15622b971ca03336dc477c133e3e240fd46e8e9246401a7",
        "at": "2026-08-16T23:50:11.789Z",
        "url": "https://www.marriott.com/en-us/hotels/indmd-le-meridien-indianapolis/overview/",
    },
}


def _intended(h):
    return OrderedDict((
        ("canonical_name", h["canonical_name"]),
        ("first_party_url", h.get("official_url") or ""),
        ("street", h.get("address") or ""),
        ("city", h.get("city") or ""),
        ("state", h.get("state") or ""),
        ("postal_code", h.get("postal_code") or ""),
        ("phone", h.get("phone") or ""),
        ("property_code", h.get("property_code") or ""),
    ))


def _rendered(**kwargs):
    return OrderedDict((
        ("page_name", kwargs.get("page_name") or ""),
        ("final_url", kwargs.get("final_url") or ""),
        ("street", kwargs.get("street") or ""),
        ("city", kwargs.get("city") or ""),
        ("state", kwargs.get("state") or ""),
        ("postal_code", kwargs.get("postal_code") or ""),
        ("phone", kwargs.get("phone") or ""),
        ("property_code", kwargs.get("property_code") or ""),
        ("source", kwargs.get("source") or ""),
    ))


def _binding(*, bound, intended, rendered, keys, notes, conflicts=None):
    return OrderedDict((
        ("bound", bound),
        ("clean_bind", bound),
        ("gate", GATE),
        ("intended", intended),
        ("rendered", rendered),
        ("independent_non_url_keys", list(keys)),
        ("url_identifier_used_as_bind", False),
        ("conflicts", list(conflicts or [])),
        ("notes", notes),
    ))


def _policy_source(kind, surface):
    return OrderedDict((
        ("kind", kind),
        ("surface", surface),
        ("first_party", True),
        ("sibling_or_brand_generic", False),
    ))


def _base(h, n, outcome, runner, rec, note, quotes=None, facts=None,
          withheld=None, contradictions=None, binding=None, final_url=None,
          policy_source=None, keep_artifact=None, service_animal_statements=None):
    art = ART.get(h["identity_key"]) if keep_artifact is not False else None
    # Uncertain rows may still have a forensic capture; publication-grade
    # artifacts stay only on clean-bind policy rows.
    if outcome == "IDENTITY_UNCERTAIN" and keep_artifact is None:
        art = None
    row = OrderedDict((
        ("decision_id", "INDY-P2-%03d" % n),
        ("queue_id", "INDY-P2-%03d" % n),
        ("hotel", h["canonical_name"]),
        ("identity_key", h["identity_key"]),
        ("corridor", h["corridor"]),
        ("brand", h.get("brand") or ""),
        ("requested_url", h.get("official_url") or ""),
        ("final_url", final_url or (art or {}).get("url") or h.get("official_url") or ""),
        ("runner_reason", runner),
        ("outcome", outcome),
        ("identity_binding", binding or {"bound": False, "clean_bind": False, "gate": GATE}),
        ("policy_source", policy_source),
        ("artifact_file", (art or {}).get("file")),
        ("artifact_sha256", (art or {}).get("html")),
        ("artifact_kind", "rendered_html" if art else None),
        ("text_sha256", (art or {}).get("text")),
        ("screenshot_sha256", (art or {}).get("png")),
        ("captured_at", (art or {}).get("at")),
        ("capture_method", "attended_browser" if art else "attended_browser_attempt"),
        ("source_grade", "PT1_FIRST_PARTY" if art else None),
        ("notes", [note]),
        ("exact_quotes", quotes or []),
        ("proposed_schema_1_2_facts", facts or []),
        ("withheld_fields", withheld or []),
        ("service_animal_statements", service_animal_statements or []),
        ("contradiction_notes", contradictions or []),
        ("recommended_founder_decision", rec),
    ))
    return row


def main() -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    by = {r["identity_key"]: r for r in census["hotels"]}
    rows = []

    comfort = by["comfort inn indianapolis airport plainfield"]
    rows.append(_base(
        comfort, 1,
        "IDENTITY_UNCERTAIN", "IDENTITY_UNVERIFIABLE", "HOLD_RETRY_IDENTITY",
        "Choice page produced no identity-bearing snapshot in 21.0s (hydration timeout). "
        "Title only is not a bind. URL path in082 is not identity. Not a refusal.",
        binding=_binding(
            bound=False, intended=_intended(comfort),
            rendered=_rendered(
                page_name="Hotel in Plainfield, IN | Comfort Inn Plainfield - Indianapolis Airport",
                final_url=comfort["official_url"],
                property_code="in082", source="page_title_only"),
            keys=[],
            notes="No JSON-LD street, city/ZIP, or phone was captured. "
                  "Property URL alone is not identity binding.")))

    courtyard_air = by["courtyard by marriott indianapolis airport"]
    rows.append(_base(
        courtyard_air, 2,
        "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Phone and URL property identifier agreed; structured street did not. "
        "IDENTITY_FAILED is a key contradiction, not a bind. No policy extracted. "
        "Sibling Marriott policy not inherited.",
        final_url="https://www.marriott.com/en-us/hotels/indca-courtyard-indianapolis-airport/overview/",
        binding=_binding(
            bound=False, intended=_intended(courtyard_air),
            rendered=_rendered(
                page_name="Courtyard by Marriott Indianapolis Airport | Hotel with Modern Rooms & Flexible Workspaces",
                final_url="https://www.marriott.com/en-us/hotels/indca-courtyard-indianapolis-airport/overview/",
                property_code="indca", source="diagnostic_only"),
            keys=["phone@structured_metadata"],
            notes="One independent non-URL key (phone). Canonical-URL code indca "
                  "was discarded. A URL-plus-phone page whose street did not agree "
                  "cannot support a policy observation.")))

    courtyard_cas = by["courtyard by marriott indianapolis castleton"]
    rows.append(_base(
        courtyard_cas, 3,
        "NEGATIVE", "CAPTURED", "APPROVE_VERIFIED_NO_PETS",
        "Official Marriott Pet Policy block states Pets Not Allowed. "
        "Service animals only is a legal access category, not a guest-pet permission. "
        "Identity bound on JSON-LD street + JSON-LD phone; URL code discarded.",
        quotes=["Pets Not Allowed", "Service animals only"],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "Pets Not Allowed", "quote_contiguous_in_artifact": True}],
        service_animal_statements=[{
            "quote": "Service animals only",
            "quote_contiguous_in_artifact": True,
            "treated_as_guest_pet_permission": False,
        }],
        contradictions=["Service animals only sits beside the refusal and is not read as a pet permission."],
        policy_source=_policy_source(
            "official_brand_property_page",
            "Marriott Castleton overview Pet Policy block on the official property page"),
        binding=_binding(
            bound=True, intended=_intended(courtyard_cas),
            rendered=_rendered(
                page_name="Courtyard by Marriott Indianapolis Castleton",
                final_url=ART["courtyard by marriott indianapolis castleton"]["url"],
                street="8670 Allisonville Road", city="Indianapolis",
                state="Indiana", postal_code="46250",
                phone="+13175769559", property_code="indcs", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches exactly. City/ZIP match. Page phone +1 317-576-9559 "
                  "has no census phone to conflict with. Runner second key was "
                  "canonical-URL indcs and was discarded.")))

    crowne = by["crowne plaza indianapolis downtown union station"]
    rows.append(_base(
        crowne, 4,
        "NEGATIVE", "POLICY_ABSENT_CONFIRMED", "APPROVE_VERIFIED_NO_PETS",
        "Property-specific IHG FAQ refusal. Independent of Crowne Plaza Airport. "
        "No service-animal sentence. Identity bound on JSON-LD street + JSON-LD phone.",
        quotes=["No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn."],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn.",
                "quote_contiguous_in_artifact": True}],
        policy_source=_policy_source(
            "property_specific_first_party_faq",
            "IHG Crowne Plaza Downtown Union Station FAQ on the official property page"),
        binding=_binding(
            bound=True, intended=_intended(crowne),
            rendered=_rendered(
                page_name="Crowne Plaza Indianapolis-Dwtn-Union Stn",
                final_url=ART["crowne plaza indianapolis downtown union station"]["url"],
                street="123 West Louisiana St.", city="Indianapolis",
                state="IN", postal_code="46225",
                phone="1-317-6312221", property_code="inddt", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="123 West Louisiana St. matches 123 West Louisiana Street. "
                  "City/ZIP match. Page phone +1 317-631-2221 has no census phone "
                  "to conflict with. Quote names Dwtn-Union Stn, not Airport. "
                  "Runner second key was canonical-URL inddt and was discarded.")))

    delta = by["delta hotels by marriott indianapolis airport"]
    rows.append(_base(
        delta, 5,
        "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Phone and URL property identifier agreed; structured street did not. "
        "IDENTITY_FAILED is a key contradiction, not a bind. No policy extracted. "
        "Sibling Marriott policy not inherited.",
        binding=_binding(
            bound=False, intended=_intended(delta),
            rendered=_rendered(
                page_name="Delta Hotels Indianapolis Airport | Hotel with Modern Rooms & Flexible Spaces",
                final_url=delta["official_url"],
                property_code="indde", source="diagnostic_only"),
            keys=["phone@structured_metadata"],
            notes="One independent non-URL key (phone). Canonical-URL code indde "
                  "was discarded. Street never agreed, so policy is withheld.")))

    fairfield = by["fairfield inn and suites indianapolis airport"]
    rows.append(_base(
        fairfield, 6,
        "NEGATIVE", "CAPTURED", "APPROVE_VERIFIED_NO_PETS",
        "Official Marriott Pet Policy block states Pets Not Allowed. "
        "A non-refundable $100 cleaning fee sits in the same block and is withheld as ambiguous. "
        "Identity bound on JSON-LD street + matching JSON-LD phone.",
        quotes=["Pets Not Allowed",
                "Non Refundable Cleaning Fee of $100.00 due at check-in."],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "Pets Not Allowed", "quote_contiguous_in_artifact": True}],
        withheld=[{"field": "other_charges.cleaning_fee",
                   "reason": "SOURCE_AMBIGUOUS",
                   "quote": "Non Refundable Cleaning Fee of $100.00 due at check-in.",
                   "note": "Appears in the Pet Policy block beside a no-pets statement; not bound as a pet charge."}],
        policy_source=_policy_source(
            "official_brand_property_page",
            "Marriott Fairfield Airport overview Pet Policy block on the official property page"),
        binding=_binding(
            bound=True, intended=_intended(fairfield),
            rendered=_rendered(
                page_name="Fairfield by Marriott Inn & Suites Indianapolis Airport",
                final_url=ART["fairfield inn and suites indianapolis airport"]["url"],
                street="5220 West Southern Avenue", city="Indianapolis",
                state="Indiana", postal_code="46241",
                phone="+13172441600", property_code="indfa", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches exactly. City/ZIP match. Phone digits 3172441600 "
                  "match census 317-244-1600. Brand-line insert in the page name "
                  "is not a different hotel. URL code discarded as a bind.")))

    hie = by["holiday inn express plainfield"]
    rows.append(_base(
        hie, 7,
        "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Official IHG pet widget is property-specific. Fee scope and pet-count "
        "scope are not stated and are withheld. Display name on the page is "
        "Holiday Inn Express Indianapolis Airport; street + phone bind it to "
        "the Plainfield census row at 6296 Cambridge Way.",
        quotes=[
            "Pets are welcome at Holiday Inn Express Indianapolis Airport.",
            "Dogs permitted with a nominal nonrefundable fee each night.",
            "Pet fee per night: 25 USD",
            "Pet weight limit: No weight limit per pet",
            "2 pets allowed",
            "Pets allowed: Only dogs allowed",
        ],
        facts=[
            {"field": "pets_allowed", "value": True,
             "quote": "Pets are welcome at Holiday Inn Express Indianapolis Airport.",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed"},
             "quote": "Pets allowed: Only dogs allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_fee",
             "value": {"amount_cents": 2500, "currency": "USD",
                       "basis": "per_night", "refundable": False},
             "quote": "Pet fee per night: 25 USD",
             "refundability_quote": "Dogs permitted with a nominal nonrefundable fee each night.",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit_stated_none", "value": True,
             "quote": "Pet weight limit: No weight limit per pet",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2,
             "quote": "2 pets allowed",
             "quote_contiguous_in_artifact": True},
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "per night is stated; per_pet vs per_room is not."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2 pets allowed does not say per room or per stay."},
        ],
        policy_source=_policy_source(
            "property_specific_first_party_faq",
            "IHG Holiday Inn Express Plainfield / Indianapolis Airport FAQ on the official property page at 6296 Cambridge Way"),
        binding=_binding(
            bound=True, intended=_intended(hie),
            rendered=_rendered(
                page_name="Holiday Inn Express Indianapolis Airport",
                final_url=ART["holiday inn express plainfield"]["url"],
                street="6296 Cambridge Way", city="Plainfield",
                state="IN", postal_code="46168",
                phone="1-317-8399000", property_code="indsw", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches exactly. City/ZIP match. Phone digits 3178399000 "
                  "match census 317-839-9000. Page name differs (Indianapolis Airport "
                  "vs Plainfield) but this is the same IHG property at 6296 Cambridge "
                  "Way, not Holiday Inn Indianapolis Airport at 8555 Stansted Drive. "
                  "Body-text code indsw is extra, not required.")))

    hi_air = by["holiday inn indianapolis airport"]
    rows.append(_base(
        hi_air, 8,
        "IDENTITY_UNCERTAIN", "IDENTITY_UNVERIFIABLE", "HOLD_RETRY_IDENTITY",
        "Official URL rendered page title '404 Experience' after 20.9s. "
        "No identity snapshot. Path segment indap is an IHG city code shared "
        "with Crowne Plaza Airport and is not a bind. Crowne Airport refusal "
        "not inherited. Not a no-pets finding.",
        binding=_binding(
            bound=False, intended=_intended(hi_air),
            rendered=_rendered(
                page_name="404 Experience",
                final_url=hi_air["official_url"],
                property_code="indap", source="page_title_only"),
            keys=[],
            notes="404/empty page cannot bind 8555 Stansted Drive. "
                  "Property URL alone is not identity binding.")))

    jw = by["jw marriott indianapolis"]
    rows.append(_base(
        jw, 9,
        "IDENTITY_UNCERTAIN", "CAPTURED", "HOLD_RETRY_IDENTITY",
        "Page did not bind cleanly. Capture-time assessor was STRONG_MATCH "
        "(name+city only); the counted address key was ZIP 46204 plus URL "
        "indjw. Street never agreed under the official parser. Policy on this "
        "page is unused. Sibling Marriott policy not inherited.",
        final_url=ART["jw marriott indianapolis"]["url"],
        keep_artifact=True,
        binding=_binding(
            bound=False, intended=_intended(jw),
            rendered=_rendered(
                page_name="JW Marriott Indianapolis",
                final_url=ART["jw marriott indianapolis"]["url"],
                street="10 S West Street", city="Indianapolis",
                state="Indiana", postal_code="46204",
                phone="+13178605800", property_code="indjw", source="jsonld"),
            keys=["phone@structured_metadata"],
            notes="Unclean bind: official street key was postal-only (46204), "
                  "second key was the URL, verdict had no address_matched. "
                  "JSON-LD street 10 S West Street was not an official street "
                  "agreement. Policy is withheld. Artifact retained for audit only.")))

    meridien = by["le meridien indianapolis"]
    rows.append(_base(
        meridien, 10,
        "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Official Marriott Pet Policy: Pets Welcome, no pet fee, 40 lb maximum "
        "with no stated scope. Generic pets is not dogs+cats. Identity bound on "
        "JSON-LD street + JSON-LD phone; URL code discarded.",
        quotes=["Pets Welcome", "Pets are welcome. No pet fee.", "Maximum Pet Weight: 40.0lbs"],
        facts=[
            {"field": "pets_allowed", "value": True,
             "quote": "Pets are welcome. No pet fee.",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_fee",
             "value": {"amount_cents": 0, "currency": "USD"},
             "quote": "Pets are welcome. No pet fee.",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 40.0, "unit": "lb", "operator": "lte"},
             "quote": "Maximum Pet Weight: 40.0lbs",
             "quote_contiguous_in_artifact": True},
        ],
        withheld=[
            {"field": "pet_fee.basis", "reason": "SOURCE_SILENT",
             "note": "No pet fee is stated; a basis is not."},
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "40.0lbs is stated without per-pet or combined."},
            {"field": "species", "reason": "SOURCE_SILENT",
             "note": "Generic pets is not dogs+cats."},
        ],
        policy_source=_policy_source(
            "official_brand_property_page",
            "Marriott Le Meridien Indianapolis overview Pet Policy block on the official property page"),
        binding=_binding(
            bound=True, intended=_intended(meridien),
            rendered=_rendered(
                page_name="Le Méridien Indianapolis",
                final_url=ART["le meridien indianapolis"]["url"],
                street="123 South Illinois Street", city="Indianapolis",
                state="Indiana", postal_code="46225",
                phone="+13177371600", property_code="indmd", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches exactly. City/ZIP match. Page phone +1 317-737-1600 "
                  "has no census phone to conflict with. Runner second key was "
                  "canonical-URL indmd and was discarded.")))

    for row in rows:
        if row["outcome"] in ("AFFIRMATIVE_STRUCTURED", "NEGATIVE"):
            bind = row["identity_binding"]
            if not bind.get("bound") or not bind.get("clean_bind"):
                raise SystemExit("policy retained without a clean bind: %s" % row["identity_key"])
            if len(bind.get("independent_non_url_keys") or []) < 2:
                raise SystemExit("policy retained without two non-URL keys: %s" % row["identity_key"])
            if bind.get("url_identifier_used_as_bind"):
                raise SystemExit("policy retained on URL identifier: %s" % row["identity_key"])
            src = row.get("policy_source") or {}
            if not src.get("first_party") or src.get("sibling_or_brand_generic"):
                raise SystemExit("policy retained from a non-first-party surface: %s"
                                 % row["identity_key"])
            for required in ("artifact_sha256", "artifact_kind", "captured_at",
                             "capture_method", "source_grade"):
                if not row.get(required):
                    raise SystemExit("usable observation missing %s: %s"
                                     % (required, row["identity_key"]))
            if not row.get("exact_quotes"):
                raise SystemExit("usable observation has no contiguous quote: %s"
                                 % row["identity_key"])
            if not all(f.get("quote") and f.get("quote_contiguous_in_artifact")
                       for f in row["proposed_schema_1_2_facts"]):
                raise SystemExit("fact missing a contiguous quote: %s"
                                 % row["identity_key"])
            for fact in row["proposed_schema_1_2_facts"]:
                if fact.get("field") != "pet_fee":
                    continue
                value = fact.get("value") or {}
                quote = (fact.get("quote") or "").lower()
                if "scope" in value and "per pet" not in quote and "per room" not in quote:
                    raise SystemExit("fee scope inferred without an explicit quote: %s"
                                     % row["identity_key"])
                refund_hay = " ".join((
                    quote,
                    (fact.get("refundability_quote") or "").lower(),
                ))
                if "refundable" in value and "refund" not in refund_hay:
                    raise SystemExit("refundability inferred without an explicit quote: %s"
                                     % row["identity_key"])
        else:
            if row["proposed_schema_1_2_facts"] or row["exact_quotes"]:
                raise SystemExit("policy used on an unbound row: %s" % row["identity_key"])

    counts = OrderedDict((
        ("AFFIRMATIVE_STRUCTURED", 2),
        ("AFFIRMATIVE_PARTIAL", 0),
        ("NEGATIVE", 3),
        ("POLICY_NOT_FOUND", 0),
        ("IDENTITY_UNCERTAIN", 5),
        ("ROUTING_PROBLEM", 0),
        ("ACCESS_BLOCKED", 0),
        ("CAPTURE_FAILED", 0),
    ))
    results = OrderedDict((
        ("schema", "ptf-indianapolis-pass2-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-16"),
        ("market_id", "indianapolis-in"),
        ("captured_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001, agent)"),
        ("capture_method",
         "attended browser (dedicated visible Chrome via official CaptureRunner); "
         "raw HTML/PNG only in gitignored "
         "data/worker_runs/pettripfinder/indianapolis-attended-capture-002/"),
        ("source_queue", "indianapolis_capture_ready_queue_002.json"),
        ("rows_total", 10),
        ("rows_captured", 6),
        ("rows_with_publication_grade_artifact", 5),
        ("hilton_rows_driven", 0),
        ("founder_decisions_applied", False),
        ("identity_gate", OrderedDict((
            ("name", GATE),
            ("rule",
             "PROPERTY URL ALONE IS NOT IDENTITY BINDING. If a page does not "
             "bind cleanly, the outcome is IDENTITY_UNCERTAIN and its policy "
             "is unused. A policy observation is retained only when JSON-LD "
             "renders a matching street and an independent non-conflicting "
             "phone, and the quote is from that property's first-party page "
             "or property-specific FAQ. A canonical-URL property code is "
             "never a bind."),
            ("rescored_from", "indianapolis-attended-capture-002 journal + capture JSON-LD"),
        ))),
        ("policy_authority", OrderedDict((
            ("accepted", [
                "exact property first-party website",
                "official brand property page",
                "property-specific first-party FAQ/policy surface",
            ]),
            ("rejected", [
                "OTA text",
                "search snippets as authority",
                "neighboring hotel policy",
                "generic brand policy",
                "sibling-property policy",
            ]),
        ))),
        ("artifact_standard", OrderedDict((
            ("usable_observation_requires", [
                "artifact_sha256",
                "artifact_kind",
                "captured_at",
                "capture_method",
                "source_grade",
                "exact contiguous quote",
                "property identity binding",
            ]),
            ("retained_media", "rendered HTML and screenshot per existing artifact contract"),
            ("raw_page_bytes",
             "outside git in data/worker_runs/pettripfinder/indianapolis-attended-capture-002/"),
        ))),
        ("extraction_doctrine", OrderedDict((
            ("rule", "SOURCE SILENCE = ABSENCE"),
            ("extract_only_if_explicit", [
                "pets_allowed", "species", "pet_count_limit", "pet_count_scope",
                "weight_limit", "combined_weight_limit", "pet_fee", "fee basis",
                "fee scope", "refundability", "fee tiers", "fee cap", "deposits",
                "cleaning fees / other charges", "breed restrictions",
                "unattended rules", "room restrictions", "reservation requirements",
                "general restrictions", "service-animal statements",
            ]),
            ("never_infer", [
                "dogs + cats from generic pets",
                "fee basis",
                "fee scope",
                "refundability",
            ]),
        ))),
        ("outcome_counts", counts),
        ("rule",
         "Only the recommended 10 non-Hilton ready-queue rows were driven. "
         "An unclean identity bind withholds policy and continues. "
         "Crowne Downtown refusal is independent of Crowne Airport. "
         "No sibling Marriott policy was inherited. No OTA or brand-generic "
         "policy was used. No founder decision was applied. No authority was written."),
        ("speed_benchmark", OrderedDict((
            ("batch_total", 10),
            ("started_at", "2026-08-16T23:31:29.696Z"),
            ("finished_at", "2026-08-16T23:50:53.080Z"),
            ("elapsed_seconds", 1179.09),
            ("captures_completed", 10),
            ("successful_artifacts", 5),
            ("median_inter_capture_gap_seconds", 106.0),
            ("captures_per_hour", 30.5),
            ("positive_rate", 0.2),
            ("negative_rate", 0.3),
            ("policy_not_found_rate", 0.0),
            ("identity_uncertain_rate", 0.5),
        ))),
        ("results", rows),
    ))
    positives = [r for r in rows if r["outcome"].startswith("AFFIRMATIVE")]
    negatives = [r for r in rows if r["outcome"] == "NEGATIVE"]
    packet = OrderedDict((
        ("schema", "ptf-indianapolis-pass2-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-16"),
        ("prepared_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001, agent)"),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("founder_decisions_applied", False),
        ("identity_gate", results["identity_gate"]),
        ("policy_authority", results["policy_authority"]),
        ("artifact_standard", results["artifact_standard"]),
        ("extraction_doctrine", results["extraction_doctrine"]),
        ("rule",
         "Nothing here is published. Founder decisions are not applied in this "
         "packet. Approving a negative would write an exclusion later. Approving "
         "a positive would write schema 1.2 facts later. Identity-uncertain rows "
         "stay unresolved and their policy is unused. A page that does not bind "
         "cleanly cannot contribute a policy observation."),
        ("positive_candidates", positives),
        ("negative_candidates", negatives),
        ("identity_uncertain",
         [r for r in rows if r["outcome"] == "IDENTITY_UNCERTAIN"]),
        ("founder_decisions_required", 10),
        ("authority_changed", False),
    ))
    (LP / "indianapolis_pass2_capture_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (LP / "indianapolis_pass2_founder_review_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
