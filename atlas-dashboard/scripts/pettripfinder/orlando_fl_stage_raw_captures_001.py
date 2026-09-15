"""PTF-ORLANDO-FL-PARALLEL-SOURCE-READY-001 -- stage live captures as committed raw inputs.

Capture-time only. Reads the operator's local capture store (passed as an
argument; nothing machine-specific is written into the outputs) and writes the
market-owned raw captures the deterministic build consumes:

    raw_captures/dbpr_lodging_inscope_001.json      Florida DBPR public-lodging licences (in-scope counties/cities) + geocodes
    raw_captures/osm_overpass_lodging_001.json      Overpass tourism=hotel|motel|resort|guest_house|hostel|apartment|chalet + building=hotel
    raw_captures/visitorlando_hotels_001.json       Visit Orlando CVB listing API, catid 167 "Hotels"
    raw_captures/hilton_inventory_001.json          hilton.com hotelSummaryOptions (26 Central Florida localities) -> compact rows
    raw_captures/marriott_owned_harvest_codes_001.json  Marriott property codes reused from the owned Dayton sitemap harvest
    raw_captures/evidence_pages_001.jsonl.gz        every first-party page adjudicated for policy (raw body + hashes)
    raw_captures/lane_attempts_001.json             per-family plain-client outcomes (refusals are facts about a moment)

Run:
    python -m scripts.pettripfinder.orlando_fl_stage_raw_captures_001 <capture_store_dir>
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET_ID = "orlando-fl"
RAW = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "staging" / MARKET_ID / "raw_captures"


def _dump(path: Path, doc) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def main(store: Path) -> int:
    ledger = {}
    for line in (store / "fetch_ledger.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        rec.pop("path", None)
        ledger.setdefault(rec["requested_url"], []).append(rec)

    # ---- DBPR
    dbpr = json.loads((store / "dbpr_inscope.json").read_text())
    for r in dbpr:
        r["source"]["file"] = r["source"]["file"]
    extracts = sorted({r["source"]["file"] for r in dbpr})
    doc = {
        "schema": "ptf-orlando-fl-raw-dbpr/1.0", "market_id": MARKET_ID,
        "source": "Florida DBPR Division of Hotels & Restaurants -- active public-lodging licence extracts (hrlodge1..7.csv)",
        "source_page": "https://www2.myfloridalicense.com/hotels-restaurants/lodging-public-records/",
        "adapter_reused": "scripts/pettripfinder/discovery/fl_dbpr_registry.py column vocabulary (owned, unmodified)",
        "extract_fetches": {u: [{k: v for k, v in a.items() if k in ("captured_at", "status", "sha256", "byte_length")} for a in ledger.get(u, [])] for u in extracts},
        "scope": "Rank codes HOTL, MOTL, TAPT, BNB in Orange, Osceola, Seminole; Lake (listed cities); Polk (listed cities); Volusia (DeLand area)",
        "geocoding": "US Census Bureau batch geocoder (Public_AR_Current) then Nominatim for non-matches; match_type recorded per row",
        "count": len(dbpr), "licences": sorted(dbpr, key=lambda r: r["license_number"]),
    }
    print("dbpr", _dump(RAW / "dbpr_lodging_inscope_001.json", doc)[:16])

    # ---- OSM
    osm_bytes = (store / "osm_orlando.json").read_bytes()
    osm = json.loads(osm_bytes)
    doc = {"schema": "ptf-orlando-fl-raw-osm/1.0", "market_id": MARKET_ID, "endpoint": "https://overpass-api.de/api/interpreter",
           "query_bbox": [27.95, -81.95, 28.95, -80.95], "raw_response_sha256": hashlib.sha256(osm_bytes).hexdigest(),
           "raw_response_bytes": len(osm_bytes), "osm3s": osm.get("osm3s"),
           "elements": sorted(osm["elements"], key=lambda e: (e["type"], e["id"]))}
    print("osm", _dump(RAW / "osm_overpass_lodging_001.json", doc)[:16])

    # ---- Visit Orlando
    vo = json.loads((store / "visitorlando_hotels.json").read_text(encoding="utf-8"))
    vo["schema"] = "ptf-orlando-fl-raw-visitorlando/1.0"
    vo["market_id"] = MARKET_ID
    vo["docs"] = sorted(vo["docs"], key=lambda d: d["recid"])
    print("vo", _dump(RAW / "visitorlando_hotels_001.json", vo)[:16])

    # ---- Hilton inventory
    gq_bytes = (store / "relay" / "hilton_inventory_graphql.json").read_bytes()
    gq = json.loads(gq_bytes)
    inv = json.loads((store / "hilton_inventory.json").read_text())
    doc = {"schema": "ptf-orlando-fl-raw-hilton-inventory/1.0", "market_id": MARKET_ID, "captured_at": gq["captured_at"], "lane": gq["lane"],
           "endpoint": gq["endpoint"], "localities": sorted(gq["responses"].keys()),
           "raw_payload_sha256": hashlib.sha256(gq_bytes).hexdigest(), "raw_payload_bytes": len(gq_bytes),
           "supplemented_by": "static hilton.com/en/locations/usa/florida/<city>/ pages (plain client) for 3 rows the query did not return",
           "hotels": sorted(inv, key=lambda r: r["property_code"])}
    print("hilton", _dump(RAW / "hilton_inventory_001.json", doc)[:16])

    # ---- Marriott owned harvest
    codes = json.loads((store / "marriott_codes.json").read_text())
    doc = {"schema": "ptf-orlando-fl-raw-marriott-owned-codes/1.0", "market_id": MARKET_ID,
           "owned_source": "atlas-dashboard/launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json @ commit 2030358b (Marriott sitemap walk, 17,567 property URLs)",
           "selection": "code prefix mco/orl/sfb or an Orlando-area locality token in the slug; non-Florida matches kept for audit and dropped by the build",
           "requests_spent": 0, "codes": dict(sorted(codes.items()))}
    print("marriott", _dump(RAW / "marriott_owned_harvest_codes_001.json", doc)[:16])

    # ---- evidence pages (Hilton relay captures + plain-client first-party pages named by the rulings)
    records = []
    for f in sorted((store / "relay").glob("hilton_*.json")):
        if "inventory" in f.name or "probe" in f.name:
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        records.append({"requested_url": rec["requested_url"], "final_url": rec.get("final_url"), "status": rec.get("status"),
                        "captured_at": rec["captured_at"], "lane": rec["lane"], "body_sha256_in_capture_context": rec.get("body_sha256"),
                        "body": rec.get("body") or ""})
    wanted = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    for u in wanted:
        attempts = [a for a in ledger.get(u, []) if a.get("status") == 200]
        if not attempts:
            continue
        a = attempts[-1]
        raw = (store / "raw" / (_key(u) + ".bin")).read_bytes()
        records.append({"requested_url": u, "final_url": a.get("final_url"), "status": 200, "captured_at": a["captured_at"],
                        "lane": a["lane"], "body_sha256_in_capture_context": hashlib.sha256(raw).hexdigest(),
                        "body_encoding": "utf-8 (errors=replace)", "body": raw.decode("utf-8", "replace")})
    records.sort(key=lambda r: r["requested_url"])
    buf = io.BytesIO()
    with gzip.GzipFile(filename="evidence_pages_001.jsonl", mode="wb", fileobj=buf, mtime=0) as gz:
        for r in records:
            r["body_sha256_utf8"] = hashlib.sha256(r["body"].encode("utf-8")).hexdigest()
            r["byte_length_utf8"] = len(r["body"].encode("utf-8"))
            gz.write((json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    (RAW / "evidence_pages_001.jsonl.gz").write_bytes(buf.getvalue())
    print("evidence pages", len(records), hashlib.sha256(buf.getvalue()).hexdigest()[:16], len(buf.getvalue()))

    # ---- lane attempts
    fam = {}
    for u, attempts in ledger.items():
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", u).split("/")[0].lower())
        for a in attempts:
            k = str(a.get("status") or a.get("error", "ERR").split(":")[0])
            fam.setdefault(host, {}).setdefault(k, 0)
            fam[host][k] += 1
    doc = {"schema": "ptf-orlando-fl-lane-attempts/1.0", "market_id": MARKET_ID,
           "note": "Plain-client outcome counts by host for this run. A refusal is a fact about a moment, never inherited.",
           "attended_browser_note": "Attended same-origin capture succeeded on hilton.com (105 hotel-info pages + inventory). Installing the same capture on marriott.com was DENIED by the operator's permission classifier this session; no attended capture was attempted on any other brand origin.",
           "hosts": dict(sorted(fam.items())),
           "url_last_status": {u: (a[-1].get("status") if a[-1].get("status") is not None else a[-1].get("error", "ERR").split(":")[0]) for u, a in sorted(ledger.items())}}
    print("lanes", _dump(RAW / "lane_attempts_001.json", doc)[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
