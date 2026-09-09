"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- probe the cheap lane before buying one.

The committed static report already measured Marriott 50/50 and Hilton 47/47
ACCESS_DENIED two days ago. That is a MEASUREMENT and not a licence to skip the
rung: a refusal goes stale in days, and the whole reason this order exists is
that an earlier order trusted a stored fact instead of a durable one.

So the ladder's first rung is probed here, live, for one URL per host in the
recovery cohort. It is free, it is bounded to one request per host, and it
writes what it observed rather than what it expected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
COHORT = os.path.join(REPORTS, "nashville_tn_recovery_cohort_003.json")
OUT = os.path.join(REPORTS, "nashville_tn_static_probe_003.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def fetch(url, timeout=30):
    """One direct first-party GET. Returns what happened, never an inference."""
    started = time.monotonic()
    request = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
            body = response.read()
            return OrderedDict((
                ("outcome", "FETCHED"),
                ("http_status", response.status),
                ("final_url", response.geturl()),
                ("byte_length", len(body)),
                ("content_sha256", hashlib.sha256(body).hexdigest()),
                ("seconds", round(time.monotonic() - started, 2)),
            )), body
    except urllib.error.HTTPError as exc:
        return OrderedDict((
            ("outcome", "ACCESS_DENIED" if exc.code in (401, 403, 429) else "HTTP_ERROR"),
            ("http_status", exc.code),
            ("final_url", url),
            ("byte_length", None),
            ("content_sha256", ""),
            ("detail", str(exc)[:200]),
            ("seconds", round(time.monotonic() - started, 2)),
        )), b""
    except Exception as exc:                                        # noqa: BLE001
        return OrderedDict((
            ("outcome", "CHANNEL_FAILURE"),
            ("http_status", None),
            ("final_url", url),
            ("byte_length", None),
            ("content_sha256", ""),
            ("detail", "%s: %s" % (type(exc).__name__, exc))[:200],
            ("seconds", round(time.monotonic() - started, 2)),
        )), b""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--per-host", type=int, default=1,
                    help="requests per host; the probe is bounded on purpose")
    args = ap.parse_args(argv)

    cohort = _load(COHORT)["recovery_cohort"]
    by_host = OrderedDict()
    for row in cohort:
        url = row["official_url"]
        if not url.startswith("http"):
            continue
        by_host.setdefault(url.split("/")[2], []).append(row)

    probes, requests = [], 0
    for host, rows in by_host.items():
        for row in rows[:args.per_host]:
            result, body = fetch(row["official_url"])
            requests += 1
            probe = OrderedDict((
                ("host", host),
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("requested_url", row["official_url"]),
                ("rows_on_this_host_in_the_cohort", len(rows)),
            ))
            probe.update(result)
            if body:
                text = body.decode("utf-8", "replace")
                probe["mentions_pet"] = "pet" in text.lower()
                probe["excerpt"] = " ".join(text[:400].split())
            probes.append(probe)

    verdict = OrderedDict()
    for host, rows in by_host.items():
        got = [p for p in probes if p["host"] == host]
        usable = [p for p in got if p["outcome"] == "FETCHED" and (p.get("byte_length") or 0) > 2000]
        verdict[host] = OrderedDict((
            ("cohort_rows", len(rows)),
            ("probed", len(got)),
            ("static_lane_usable", bool(usable)),
            ("observed", sorted({p["outcome"] for p in got})),
            ("http_status", sorted({p.get("http_status") for p in got})),
        ))

    doc = OrderedDict((
        ("schema", "ptf-static-probe/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("lane", "DIRECT_STATIC (free)"),
        ("why_probe_at_all",
         "the committed static report measured Marriott 50/50 and Hilton 47/47 ACCESS_DENIED on "
         "2026-09-07. A refusal goes stale in days, and this order exists because an earlier one "
         "trusted a stored fact instead of a durable one. So the rung is probed live, bounded to "
         "%d request(s) per host." % args.per_host),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", requests),
        ("verdict_by_host", verdict),
        ("probes", probes),
    ))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for host, v in verdict.items():
        print("%-22s cohort %-3d probed %d -> %s %s | static usable: %s"
              % (host, v["cohort_rows"], v["probed"], v["observed"], v["http_status"],
                 v["static_lane_usable"]))
    print("free requests:", requests, "| paid calls: 0 | $0.00")
    print("written      :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
