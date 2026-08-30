"""PTF-PITTSBURGH-PASS4-ROUTING-AND-RECAPTURE-PREP-001.

Records only identity-routing, a Sunnyledge recapture result, and a safe next
capture queue.  It intentionally never writes policy facts, exclusions, or
approvals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import identity_routing as IR

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
MARKET = "pittsburgh-pa"
WORK_ORDER = "PTF-PITTSBURGH-PASS4-ROUTING-AND-RECAPTURE-PREP-001"
AS_OF = "2026-08-17"
PARTITION = LP / "pittsburgh_final_partition_001.json"
CENSUS = LP / "identity_census" / "pittsburgh-pa.json"
REPORT = LP / "markets" / "reports" / "pittsburgh_pass4_routing_recap_prep_001.json"
QUEUE = LP / "markets" / "reports" / "pittsburgh_pass4_claude_capture_queue.json"
SUNNYLEDGE_ARTIFACT = ROOT / "data" / "operator_evidence" / "pittsburgh-pass4-routing-and-recapture-prep-001" / "sunnyledge-domain-redirect-2026-08-17.txt"
SUNNYLEDGE_RELATIVE_ARTIFACT = "data/operator_evidence/pittsburgh-pass4-routing-and-recapture-prep-001/sunnyledge-domain-redirect-2026-08-17.txt"

# These URLs were recovered from exact first-party property surfaces during
# this work order.  They say only WHERE to ask; no policy content belongs here.
ROUTE_SPECS = OrderedDict([
    ("courtyard by marriott pittsburgh airport", ("https://www.marriott.com/en-us/hotels/pitca-courtyard-pittsburgh-airport/overview/", "MARRIOTT", "PITCA")),
    ("courtyard by marriott pittsburgh airport settlers ridge", ("https://www.marriott.com/en-us/hotels/pitsr-courtyard-pittsburgh-airport-settlers-ridge/overview/", "MARRIOTT", "PITSR")),
    ("motel 6 pittsburgh", ("https://www.motel6.com/property/motel-pittsburgh-pa-pennsylvania-us-294550/", "MOTEL_6", "")),
    ("sonesta simply suites pittsburgh airport", ("https://www.sonesta.com/sonesta-simply-suites/pa/pittsburgh/sonesta-simply-suites-pittsburgh-airport", "SONESTA", "")),
    ("springhill suites pittsburgh airport", ("https://www.marriott.com/en-us/hotels/pitha-springhill-suites-pittsburgh-airport/overview/", "MARRIOTT", "PITHA")),
    ("towneplace suites pittsburgh airport robinson township", ("https://www.marriott.com/en-us/hotels/pittw-towneplace-suites-pittsburgh-airport-robinson-township/overview/", "MARRIOTT", "PITTW")),
])


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def unresolved_buckets(items: list[dict]) -> dict:
    state_to_bucket = {
        "AWAITING_IDENTITY_RESOLUTION": "IDENTITY_REVIEW",
        "AWAITING_PROPERTY_LEVEL_URL": "PROPERTY_LEVEL_URL_UPGRADE",
        "AWAITING_OFFICIAL_URL": "ROUTING_RECOVERY",
        "AWAITING_POLICY_OBSERVATION": "POLICY_OBSERVATION_READY",
        "AWAITING_CENSUS_REVIEW": "CENSUS_REVIEW",
    }
    result = Counter(state_to_bucket.get(item["final_state"], "OTHER") for item in items if not item["resolved"])
    return {key: result.get(key, 0) for key in (
        "IDENTITY_REVIEW", "PROPERTY_LEVEL_URL_UPGRADE", "ROUTING_RECOVERY",
        "POLICY_OBSERVATION_READY", "SPECIAL_ACCESS", "CENSUS_REVIEW", "OTHER")}


def route_record(census_row: dict, spec: tuple[str, str, str]) -> dict:
    url, brand, property_code = spec
    route = OrderedDict([
        ("routing_id", "route-pittsburgh-pa-" + census_row["slug"]),
        ("schema_version", "1.0.0"),
        ("hotel_ref", OrderedDict([
            ("identity_key", census_row["identity_key"]), ("market_id", MARKET),
            ("canonical_name", census_row["canonical_name"]),
            ("normalized_name", census_row["normalized_name"]),
        ])),
        ("market_id", MARKET), ("official_property_url", url),
        ("official_domain", IR.registrable_domain(url)), ("brand", brand),
        # The exact endpoints and Marriott property codes are first-party
        # locator evidence.  This routing pass deliberately did not retain
        # rendered property-page bytes, so it must not overstate that evidence
        # as PAGE_RENDERED.
        ("binding_method", IR.BINDING_BRAND_INDEX),
        ("binding_sources", [
            "Official brand/property locator endpoint recovered during %s" % WORK_ORDER,
            url,
        ]),
        ("identity_signals_matched", [
            "name=" + census_row["canonical_name"], "street=" + census_row["address"],
            "city=" + census_row["city"], "zip=" + census_row["postal_code"],
            "phone=" + census_row["phone"],
        ]),
        ("identity_context", OrderedDict((key, census_row[key]) for key in
            ("address", "city", "state", "postal_code", "phone"))),
        ("observed_at", AS_OF), ("verified_at", AS_OF),
        ("property_identity_check", "PASS"),
        ("status", IR.ROUTING_CONFIRMED), ("category", "accommodation"),
        ("notes", "URL and property identity recovered without reading or recording pet-policy content."),
    ])
    if property_code:
        route["property_code"] = property_code
    return route


def build() -> tuple[dict, dict, dict]:
    partition = load(PARTITION)
    census = {row["identity_key"]: row for row in load(CENSUS)["hotels"]}
    items = partition["items"]
    counts = Counter(item["final_state"] for item in items)
    assert (counts["PUBLISHED_PET_FRIENDLY"], counts["VERIFIED_NO_PETS"],
            counts["OUT_OF_CURRENT_CATEGORY"]) == (29, 6, 3)
    assert sum(count for state, count in counts.items() if state.startswith("AWAITING_")) == 58
    existing_routes = MA.load_market_routes(MARKET)
    # Permit a deterministic rerun after application, but fail closed if a
    # different Pittsburgh routing batch has appeared.
    assert len(existing_routes) in (0, len(ROUTE_SPECS))
    if existing_routes:
        assert {route["hotel_ref"]["identity_key"] for route in existing_routes} == set(ROUTE_SPECS)

    unresolved = [item for item in items if not item["resolved"]]
    identity = [item for item in unresolved if item["final_state"] == "AWAITING_IDENTITY_RESOLUTION"]
    assert len(identity) == 38
    identity_results = [OrderedDict([
        ("identity_key", item["identity_key"]), ("outcome", "IDENTITY_UNRESOLVED"),
        ("reason", "No new current first-party identity binding was captured in this routing-only pass."),
    ]) for item in identity]

    routes = [route_record(census[key], spec) for key, spec in ROUTE_SPECS.items()]
    IR.validate_authority(MA.build_routing_shard(MARKET, routes, [WORK_ORDER]))
    routing_unresolved = [
        item["identity_key"] for item in unresolved
        if item["final_state"] == "AWAITING_OFFICIAL_URL" and item["identity_key"] not in ROUTE_SPECS
    ]
    assert len(routing_unresolved) == 3

    artifact_text = SUNNYLEDGE_ARTIFACT.read_text(encoding="utf-8")
    artifact_sha = sha256(SUNNYLEDGE_ARTIFACT)
    assert "final_url: https://www.hugedomains.com/" in artifact_text
    assert "SunnyLedge.com is for sale" in artifact_text
    sunnyledge = OrderedDict([
        ("identity_key", "sunnyledge boutique hotel"), ("outcome", "SOURCE_AMBIGUOUS"),
        ("publication_grade", False), ("requested_url", "https://sunnyledge.com/"),
        ("final_url", "https://www.hugedomains.com/domain_profile.cfm?d=sunnyledge.com"),
        ("artifact_file", SUNNYLEDGE_RELATIVE_ARTIFACT), ("artifact_kind", "official_domain_redirect_rendered_text"),
        ("artifact_sha256", artifact_sha), ("captured_at", AS_OF),
        ("capture_method", "attended_browser_rendered_dom"),
        ("identity_binding", "Expected hotel: Sunnyledge Boutique Hotel | 5124 Fifth Avenue, Pittsburgh, PA 15232 | +1 412-683-5014. Final page is a third-party parked-domain sale page and does not bind that identity."),
        ("exact_quotes", ["SunnyLedge.com", "This domain is for sale: $10,595"]),
        ("next_action", "RECAPTURE_REQUIRED"),
    ])

    # Exact policy-ready rows, excluding Sunnyledge after its ambiguous result.
    policy_ready = [item["identity_key"] for item in unresolved
                    if item["final_state"] == "AWAITING_POLICY_OBSERVATION"
                    and item["identity_key"] != "sunnyledge boutique hotel"]
    assert len(policy_ready) == 6
    readiness = OrderedDict()
    for key in ROUTE_SPECS:
        readiness[key] = "FRESH_SESSION_REQUIRED"
    for key in policy_ready:
        readiness[key] = "SPECIAL_SURFACE_REQUIRED" if key.startswith("hyatt ") else "ATTENDED_REQUIRED"
    queue_items = []
    for number, key in enumerate(readiness, 1):
        row = census[key]
        queue_items.append(OrderedDict([
            ("row_number", number), ("identity_key", key), ("canonical_name", row["canonical_name"]),
            ("official_property_url", ROUTE_SPECS[key][0] if key in ROUTE_SPECS else row["official_url"]),
            ("address", row["address"]), ("city", row["city"]), ("state", row["state"]),
            ("postal_code", row["postal_code"]), ("phone", row["phone"]),
            ("capture_readiness", readiness[key]),
            ("policy_instruction", "Capture only a property-specific first-party pet-policy surface; do not infer any absent fact."),
        ]))
    assert len(queue_items) == 12
    report = OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-routing-recap-prep/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("authority_freeze", {"published": 29, "verified_no_pets": 6, "out_of_category": 3}),
        ("unresolved_before", 58), ("unresolved_buckets_before", unresolved_buckets(items)),
        ("sunnyledge_recapture", sunnyledge), ("identity_review", identity_results),
        ("routing_confirmed", list(ROUTE_SPECS)), ("routing_unresolved", routing_unresolved),
        ("census_review", [item["identity_key"] for item in unresolved if item["final_state"] == "AWAITING_CENSUS_REVIEW"]),
        ("capture_readiness_counts", dict(Counter(readiness.values()))),
        ("queue_note", "Twelve rows meet the strict identity/routing gate. The requested 20-30 target is not padded with unresolved identity, census-review, routing-unresolved, or Sunnyledge rows."),
    ])
    queue = OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-claude-capture-queue/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("count", len(queue_items)), ("items", queue_items),
    ])
    return routes, report, queue


def apply() -> None:
    routes, report, queue = build()
    MA._write_if_changed(MA.routing_shard_path(MARKET), MA.render_json(
        MA.build_routing_shard(MARKET, routes, [WORK_ORDER])))
    MA.write_generated_artifacts()
    assert MA.check_generated_artifacts() == []
    dump(REPORT, report)
    dump(QUEUE, queue)
    print("PASS4 routing prep: routes=6 queue=12 authority unchanged=29/6/3")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    routes, report, queue = build()
    if args.apply:
        apply()
    else:
        print(json.dumps({"routes": len(routes), "queue": queue["count"], "buckets": report["unresolved_buckets_before"]}, indent=1))


if __name__ == "__main__":
    main()
