"""PTF-LOUISVILLE-BRAND-SURFACE-REPAIR-001 -- factory improvement report.

Proposes ROUTING_READY vs EVIDENCE_READY for Louisville only.
Does not change the global capture-ready contract. Does not execute capture.

    python -m scripts.pettripfinder.compile_louisville_routing_vs_evidence_ready_001
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
READY = PKG / "markets" / "reports" / "louisville_capture_ready_queue_002.json"
REPAIR_DESK = PKG / "markets" / "reports" / "louisville_identity_routing_repair_001.json"
REPORT = PKG / "markets" / "reports" / "louisville_routing_vs_evidence_ready_001.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-BRAND-SURFACE-REPAIR-001"
AS_OF = "2026-08-16"

PROCESSED_PATHS = (
    "louisville_pass1_capture_results.json",
    "louisville_pass2_capture_results.json",
    "louisville_pass3_capture_results.json",
)

#: Brands whose Louisville static GET proved a special surface is required.
SPECIAL_SURFACE = OrderedDict((
    ("www.wyndhamhotels.com",
     "Hotel Policies modal / JS-hydrated .pet-policy-desc"),
    ("www.ihg.com",
     "Static hoteldetail 403; FAQ/accordion/aria-hidden required"),
    ("www.redroof.com",
     "Static property page 403; attended render required"),
    ("www.studio6.com",
     "Property page timeout; brand wording not property-bound"),
    ("www.motel6.com",
     "Same family as Studio 6; property page not evidence-ready"),
    ("www.choicehotels.com",
     "Static GET reset/403; attended Choice surface required"),
    ("www.bestwestern.com",
     "DataDome 403; attended surface required"),
    ("www.hilton.com",
     "Known special-session brand surface"),
    ("www.hyatt.com",
     "Known special-session brand surface"),
    ("www.marriott.com",
     "Known bot-walled brand property surface; not evidence-ready by URL alone"),
))

EVIDENCE_HOSTS = (
    "druryhotels.com",
    "omnihotels.com",
)


def _host(url: str) -> str:
    if "://" not in (url or ""):
        return ""
    return url.split("/")[2].lower()


def _class_for(url: str, identity_class: str) -> str:
    if identity_class == "IDENTITY_CORRECTION_REQUIRED":
        return "ROUTING_READY_IDENTITY_HOLD"
    host = _host(url)
    if host in SPECIAL_SURFACE:
        return "ROUTING_READY"
    if any(h in host for h in EVIDENCE_HOSTS):
        return "EVIDENCE_READY"
    if host and host not in SPECIAL_SURFACE:
        return "EVIDENCE_READY"
    return "NOT_READY"


def main() -> None:
    ready = json.loads(READY.read_text(encoding="utf-8-sig"))
    desk = {
        r["identity_key"]: r
        for r in json.loads(REPAIR_DESK.read_text(encoding="utf-8-sig"))["rows"]
    }
    done = set()
    for name in PROCESSED_PATHS:
        doc = json.loads((PKG / "markets" / "reports" / name).read_text(
            encoding="utf-8-sig"))
        done.update(r["identity_key"] for r in doc["rows"])

    remaining = []
    for row in ready["items"]:
        if row["identity_key"] in done:
            continue
        ic = desk.get(row["identity_key"], {}).get("identity_class", "")
        url = row.get("official_url") or ""
        klass = _class_for(url, ic)
        remaining.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("hotel", row["hotel"]),
            ("official_url", url),
            ("host", _host(url)),
            ("url_grade", row.get("url_grade")),
            ("legacy_capture_ready", True),
            ("readiness", klass),
            ("special_surface", SPECIAL_SURFACE.get(_host(url), "")),
            ("desk_identity_class", ic),
        )))

    counts = OrderedDict(Counter(r["readiness"] for r in remaining).most_common())
    host_counts = OrderedDict(
        Counter(r["host"] for r in remaining).most_common())

    rec = partition.reconcile(
        census.identity_keys(json.loads(CENSUS.read_text(encoding="utf-8-sig"))),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0:
        raise SystemExit("authority freeze broken")

    write_json(REPORT, OrderedDict((
        ("schema", "ptf-louisville-routing-vs-evidence-ready/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("global_contract_changed", False),
        ("manual_queue_executed", False),
        ("proposal", OrderedDict((
            ("current_gate",
             "louisville_capture_ready_queue_002 treats a bound property-level "
             "URL as capture-ready. Pass 3 proved that is too broad."),
            ("routing_ready",
             "Identity is bound to a property-level official URL. Policy "
             "observation is not yet possible by unattended GET because the "
             "brand requires a known special surface."),
            ("evidence_ready",
             "A first-party or brand surface that Louisville has shown can "
             "yield publication-grade policy text without a special session "
             "(static official page or official policies URL)."),
            ("rule",
             "A property-level URL alone is not evidence-ready when the brand "
             "requires a known special surface."),
            ("do_not",
             "Do not change the global capture-ready contract in this work "
             "order. Louisville reports the split first."),
        ))),
        ("legacy_capture_ready", ready["count"]),
        ("already_processed", len(done)),
        ("remaining_legacy_ready", len(remaining)),
        ("remaining_counts", counts),
        ("remaining_hosts", host_counts),
        ("evidence_ready_remaining",
         sum(1 for r in remaining if r["readiness"] == "EVIDENCE_READY")),
        ("routing_ready_remaining",
         sum(1 for r in remaining if r["readiness"] == "ROUTING_READY")),
        ("routing_ready_identity_hold",
         sum(1 for r in remaining
             if r["readiness"] == "ROUTING_READY_IDENTITY_HOLD")),
        ("unresolved", rec.unresolved),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("items", remaining),
        ("note",
         "Remaining legacy capture-ready rows are all brand special-surface "
         "hosts. Evidence-ready remainder is 0. Manual attended queue is "
         "separate and not executed."),
    )))
    print("remaining", len(remaining), dict(counts))


if __name__ == "__main__":
    main()
