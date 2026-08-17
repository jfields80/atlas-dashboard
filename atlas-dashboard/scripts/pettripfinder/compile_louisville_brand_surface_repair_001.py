"""PTF-LOUISVILLE-BRAND-SURFACE-REPAIR-001.

Reclassify Pass 3 surfaces and prepare a brand-specific attended queue.
Does not recapture, apply authority, merge, or deploy.

    python -m scripts.pettripfinder.compile_louisville_brand_surface_repair_001
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
P3 = PKG / "markets" / "reports" / "louisville_pass3_capture_results.json"
REPAIR = PKG / "markets" / "reports" / "louisville_brand_surface_repair_001.json"
QUEUE = PKG / "markets" / "reports" / "louisville_manual_capture_queue_001.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-BRAND-SURFACE-REPAIR-001"
AS_OF = "2026-08-16"

WYNDHAM = {
    "baymont by wyndham louisville airport south": (
        "WYNDHAM", "46926", "6515 Signature Drive, Louisville, KY 40213"),
    "hawthorn suites by wyndham louisville east": (
        "WYNDHAM", "30812", "751 Cypress Station Drive, Louisville, KY 40207"),
    "travelodge by wyndham sellersburg louisville north": (
        "WYNDHAM", "06030", "7618 Old State Road 60, Sellersburg, IN 47172"),
    "super 8 by wyndham louisville airport": (
        "WYNDHAM", "03586", "4800 Preston Highway, Louisville, KY 40213"),
    "la quinta inn and suites by wyndham louisville northeast old henry": (
        "WYNDHAM", "53765", "13825 Terra View Trl, Louisville, KY 40245"),
}
IHG = {
    "holiday inn express and suites jeffersonville":
        ("IHG", "INDJV"),
    "staybridge suites louisville east":
        ("IHG", "SDFMT"),
    "candlewood suites louisville airport":
        ("IHG", "SDFGL"),
}
RED_ROOF = {
    "red roof inn louisville expo airport": "rri118",
    "red roof inn louisville hurstbourne": "rri034",
}


def _wyndham(row):
    brand, pid, addr = WYNDHAM[row["identity_key"]]
    url = row["final_url"]
    return OrderedDict((
        ("decision_id", row["decision_id"]),
        ("hotel", row["hotel"]),
        ("identity_key", row["identity_key"]),
        ("brand", brand),
        ("official_url", row["queued_url"]),
        ("final_url", url),
        ("corrected_property_url",
         url if row["identity_key"].startswith("la quinta") else ""),
        ("pass3_outcome", row["outcome"]),
        ("reclassified_outcome", "ATTENDED_POLICY_SURFACE"),
        ("page_identity_binding", row["identity_binding"]),
        ("property_id", pid),
        ("exact_failure_mode",
         "STATIC_POLICY_SLOT_EMPTY. Property page binds identity. "
         "Hotel Policies modal (#hotelPoliciesLightbox) and "
         ".pet-policy-desc exist but are JS-hydrated and empty in the "
         "static HTML."),
        ("policy_wording_observed", False),
        ("materially_different_path_exists", True),
        ("retain_policy_not_found", False),
        ("expected_policy_surface",
         "Hotel Policies lightbox / Pet & Service Animal Policy slot"),
        ("browser_path",
         "Open the bound property overview. Click Hotel Policies. Wait for "
         "the Pet & Service Animal Policy row to hydrate. Save rendered HTML."),
        ("identity_check", addr),
        ("artifact_requirement",
         "Publication-grade rendered HTML containing a contiguous pet-policy "
         "quote plus name/street/ZIP. Do not use brand pet-friendly pages."),
        ("session_caution",
         "One fresh desktop session per property. Do not reuse a blocked "
         "static GET."),
    ))


def _ihg(row):
    brand, code = IHG[row["identity_key"]]
    return OrderedDict((
        ("decision_id", row["decision_id"]),
        ("hotel", row["hotel"]),
        ("identity_key", row["identity_key"]),
        ("brand", brand),
        ("official_url", row["queued_url"]),
        ("final_url", row["final_url"]),
        ("corrected_property_url", ""),
        ("pass3_outcome", row["outcome"]),
        ("reclassified_outcome", "ATTENDED_REQUIRED"),
        ("page_identity_binding", row["identity_binding"]),
        ("property_code", code),
        ("exact_failure_mode",
         "IHG_403_STATIC_FETCH. Generic hoteldetail GET returned 403. "
         "FAQ / pet-policy accordion / aria-hidden HTML was not read."),
        ("policy_wording_observed", False),
        ("materially_different_path_exists", True),
        ("retain_policy_not_found", False),
        ("expected_policy_surface",
         "Property FAQ / pet-policy accordion and aria-hidden rendered nodes"),
        ("browser_path",
         "Fresh session. Open the exact property page. Expand FAQ / pet "
         "policy. Inspect aria-hidden content. Save rendered HTML. Do not "
         "retry the blocked static GET."),
        ("identity_check",
         "Confirm property code %s plus street/city/ZIP before quoting."
         % code),
        ("artifact_requirement",
         "Rendered publication-grade HTML. Staybridge ladders stay "
         "structural. No sibling IHG inheritance."),
        ("session_caution",
         "Fresh session. Do not loop the same 403 route."),
    ))


def _redroof(row):
    code = RED_ROOF[row["identity_key"]]
    return OrderedDict((
        ("decision_id", row["decision_id"]),
        ("hotel", row["hotel"]),
        ("identity_key", row["identity_key"]),
        ("brand", "RED_ROOF"),
        ("official_url", row["queued_url"]),
        ("final_url", row["final_url"]),
        ("corrected_property_url", ""),
        ("pass3_outcome", row["outcome"]),
        ("reclassified_outcome", "ATTENDED_REQUIRED"),
        ("page_identity_binding", row["identity_binding"]),
        ("property_code", code),
        ("exact_failure_mode",
         "REDROOF_403_STATIC_FETCH. No publication-grade HTML retained. "
         "Official-index wording was not used as an artifact."),
        ("policy_wording_observed", False),
        ("materially_different_path_exists", True),
        ("retain_policy_not_found", False),
        ("expected_policy_surface",
         "Exact property page Hotel Policies / pet block for %s" % code),
        ("browser_path",
         "Attended open of the exact property URL. Capture this property "
         "only. If first-pet-free / second-pet schedule appears, bind it "
         "only if this page states it."),
        ("identity_check",
         "Confirm %s plus street/ZIP on the rendered page." % code),
        ("artifact_requirement",
         "Publication-grade rendered HTML from THIS property URL. Do not "
         "inherit Cleveland/Columbus Red Roof schedules."),
        ("session_caution",
         "Attended browser. Do not reuse the blocked static GET."),
    ))


def main() -> None:
    p3 = json.loads(P3.read_text(encoding="utf-8-sig"))
    by = {r["identity_key"]: r for r in p3["rows"]}
    if len(by) != 12:
        raise SystemExit("expected 12 Pass 3 rows")

    builders = {
        "myriad hotel": lambda row: OrderedDict((
            ("decision_id", row["decision_id"]),
            ("hotel", row["hotel"]),
            ("identity_key", row["identity_key"]),
            ("brand", "INDEPENDENT"),
            ("official_url", row["queued_url"]),
            ("final_url", row["final_url"]),
            ("corrected_property_url", ""),
            ("pass3_outcome", row["outcome"]),
            ("reclassified_outcome", "POLICY_NOT_FOUND"),
            ("page_identity_binding", row["identity_binding"]),
            ("exact_failure_mode",
             "FIRST_PARTY_SILENCE. Home and rooms contain no pet wording. "
             "FAQ/policies/amenities/stay URLs 404 or lack policy text. "
             "Hilton Tapestry was not used."),
            ("policy_wording_observed", False),
            ("materially_different_path_exists", False),
            ("retain_policy_not_found", True),
            ("expected_policy_surface", ""),
            ("browser_path", ""),
            ("identity_check", "900 Baxter Ave, Louisville, KY 40204"),
            ("artifact_requirement", ""),
            ("session_caution",
             "Do not keep retrying Myriad first-party pages."),
        )),
        "studio 6 louisville airport expo center": lambda row: OrderedDict((
            ("decision_id", row["decision_id"]),
            ("hotel", row["hotel"]),
            ("identity_key", row["identity_key"]),
            ("brand", "STUDIO6"),
            ("official_url", row["queued_url"]),
            ("final_url", row["final_url"]),
            ("corrected_property_url", ""),
            ("pass3_outcome", row["outcome"]),
            ("reclassified_outcome", "ATTENDED_REQUIRED"),
            ("page_identity_binding", row["identity_binding"]),
            ("exact_failure_mode",
             "STUDIO6_TIMEOUT_ZERO_BYTES. Property page never loaded. "
             "Brand Motel 6 / Studio 6 wording was not observed and is "
             "not bound."),
            ("policy_wording_observed", False),
            ("materially_different_path_exists", True),
            ("retain_policy_not_found", False),
            ("policy_specificity",
             "UNKNOWN_UNTIL_PROPERTY_PAGE_BINDS. Do not publish generic "
             "brand wording as property authority."),
            ("expected_policy_surface",
             "Exact studio6.com property page after attended load"),
            ("browser_path",
             "Attended open of the exact property URL. Confirm 571 "
             "Phillips Lane / 40209 before reading any pet text. If only "
             "brand-level wording appears without property binding, "
             "withhold it."),
            ("identity_check",
             "571 Phillips Lane, Louisville, KY 40209, 502-361-5008"),
            ("artifact_requirement",
             "Rendered publication-grade HTML of THIS property URL."),
            ("session_caution", "Do not loop the timed-out static GET."),
        )),
    }
    rows = []
    for row in p3["rows"]:
        key = row["identity_key"]
        if key in WYNDHAM:
            rows.append(_wyndham(row))
        elif key in IHG:
            rows.append(_ihg(row))
        elif key in RED_ROOF:
            rows.append(_redroof(row))
        else:
            rows.append(builders[key](row))

    keys = [r["identity_key"] for r in rows]
    if len(keys) != 12 or len(set(keys)) != 12:
        raise SystemExit("12/12 uniqueness failed")
    if set(keys) != set(by):
        raise SystemExit("Pass 3 membership mismatch")

    rec = partition.reconcile(
        census.identity_keys(json.loads(CENSUS.read_text(encoding="utf-8-sig"))),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0:
        raise SystemExit("authority freeze broken")

    counts = OrderedDict()
    for r in rows:
        counts[r["reclassified_outcome"]] = counts.get(
            r["reclassified_outcome"], 0) + 1
    write_json(REPAIR, OrderedDict((
        ("schema", "ptf-louisville-brand-surface-repair/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Reclassify Pass 3 surfaces. No recapture. No authority apply. "
         "Wyndham empty static slots are attended policy surfaces, not "
         "final POLICY_NOT_FOUND."),
        ("pass3_batch_total", 12),
        ("reclassified_counts", counts),
        ("retained_policy_not_found", 1),
        ("attended_policy_surface", 5),
        ("attended_required", 6),
        ("authority_changed", False),
        ("generic_capture_rerun", False),
        ("rows", rows),
    )))

    queue = [r for r in rows if r["reclassified_outcome"] != "POLICY_NOT_FOUND"]
    write_json(QUEUE, OrderedDict((
        ("schema", "ptf-louisville-manual-capture-queue/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("executed", False),
        ("count", len(queue)),
        ("excluded_from_queue", ["myriad hotel"]),
        ("note",
         "Brand-specific attended/manual queue only. Not executed. "
         "Myriad retained POLICY_NOT_FOUND and is not requeued."),
        ("items", [
            OrderedDict((
                ("order", i),
                ("identity_key", r["identity_key"]),
                ("hotel", r["hotel"]),
                ("brand", r["brand"]),
                ("reclassified_outcome", r["reclassified_outcome"]),
                ("exact_property_url",
                 r["corrected_property_url"] or r["final_url"]),
                ("browser_path", r["browser_path"]),
                ("expected_policy_surface", r["expected_policy_surface"]),
                ("interaction_instructions", r["browser_path"]),
                ("identity_check", r["identity_check"]),
                ("artifact_requirement", r["artifact_requirement"]),
                ("rate_limit_session_caution", r["session_caution"]),
            ))
            for i, r in enumerate(queue, start=1)
        ]),
    )))
    print("repair", 12, "queue", len(queue), "pnf", 1)


if __name__ == "__main__":
    main()
